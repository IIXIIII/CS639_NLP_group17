import enum

import requests

from src.typings import *
from src.utils import *
from .agent import AgentClient


class TaskError(enum.Enum):
    START_FAILED = "START_FAILED"
    INTERACT_FAILED = "INTERACT_FAILED"
    AGENT_FAILED = "AGENT_FAILED"
    NETWORK_ERROR = "NETWORK_ERROR"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class TaskClient:
    def __init__(
        self, name: str, controller_address: str = "http://localhost:5000/api", *_, **__,
    ) -> None:
        self.name = name
        self.controller_address = controller_address
        print("TaskClient created: {} ({})".format(name, controller_address))

    def get_indices(self) -> List[SampleIndex]:
        result = requests.get(
            self.controller_address + "/get_indices", params={"name": self.name}
        )
        if result.status_code != 200:
            raise AgentBenchException(result.text, result.status_code, self.name)
        return result.json()

    def get_concurrency(self) -> int:
        try:
            result = requests.get(
                self.controller_address + "/list_workers"
            )
        except Exception as e:
            print(ColorMessage.yellow(f"Warning task {self.name} cannot connect to controller {e}"))
            return 0
        if result.status_code != 200:
            raise AgentBenchException(result.text, result.status_code, self.name)
        result = result.json()
        if self.name not in result:
            print(ColorMessage.yellow(f"task {self.name} not found in worker list"))
            return 0
        concurrency = 0
        for worker in result[self.name]["workers"].values():
            if worker["status"] == WorkerStatus.ALIVE.name:
                concurrency += worker["capacity"] - worker["current"]
        return concurrency

    def _get_worker_address(self) -> str:
        """Get the address of an ALIVE worker for direct interact calls."""
        try:
            result = requests.get(self.controller_address + "/list_workers")
            workers = result.json().get(self.name, {}).get("workers", {})
            for worker in workers.values():
                if worker["status"] == WorkerStatus.ALIVE.name:
                    return worker["address"]
        except Exception:
            pass
        return self.controller_address  # fallback to controller

    def run_sample(self, index: SampleIndex, agent: AgentClient) -> TaskClientOutput:
        worker_address = self._get_worker_address()
        try:
            result = requests.post(
                self.controller_address + "/start_sample",
                json=StartSampleRequest(name=self.name, index=index).dict(),
            )
        except Exception as e:
            return TaskClientOutput(error=TaskError.NETWORK_ERROR.value, info=str(e))
        if result.status_code == 406:
            return TaskClientOutput(error=TaskError.NOT_AVAILABLE.value, info=result.text)
        if result.status_code != 200:
            return TaskClientOutput(error=TaskError.START_FAILED.value, info=result.text)

        # New agentrl API: session_id is in response header, body has {messages, tools, finish}
        sid_header = result.headers.get("session_id")
        if sid_header is None:
            return TaskClientOutput(error=TaskError.START_FAILED.value, info="No session_id in response header")
        sid = int(sid_header)

        data = result.json()
        messages = data.get("messages", [])
        tools = data.get("tools", [])
        finish = data.get("finish", False)
        status_str = data.get("status", SampleStatus.RUNNING.value)
        env_out = data

        while not finish:
            try:
                agent_messages = agent.inference(messages, tools=tools)
                if isinstance(agent_messages, str):
                    agent_messages = [{"role": "assistant", "content": agent_messages}]
            except AgentContextLimitException:
                requests.post(worker_address + "/cancel", json={"session_id": sid})
                return TaskClientOutput(error=TaskError.AGENT_FAILED.value, info="Agent context limit reached")
            except Exception as e:
                model_name = getattr(agent, "name", agent.__class__.__name__)
                print(f"ERROR: {model_name}/{self.name} agent error", e)
                requests.post(worker_address + "/cancel", json={"session_id": sid})
                return TaskClientOutput(error=TaskError.AGENT_FAILED.value, info=str(e))

            try:
                result = requests.post(
                    worker_address + "/interact",
                    json={"session_id": sid, "messages": agent_messages},
                )
            except Exception as e:
                return TaskClientOutput(error=TaskError.NETWORK_ERROR.value, info=str(e))

            if result.status_code != 200:
                requests.post(worker_address + "/cancel", json={"session_id": sid})
                return TaskClientOutput(error=TaskError.INTERACT_FAILED.value, info=result.text)

            data = result.json()
            env_out = data.get("env_out", data)
            new_messages = env_out.get("messages", [])
            tools = env_out.get("tools", tools)
            finish = env_out.get("finish", True)
            status_str = env_out.get("status", SampleStatus.COMPLETED.value)
            messages = messages + agent_messages + new_messages

        try:
            status = SampleStatus(status_str)
        except ValueError:
            status = SampleStatus.COMPLETED

        metric = env_out.get("metric", {})
        score = metric.get("score", 0.0)
        result_dict = {
            **metric,
            "result": score >= 1.0,   # needed by calculate_overall
            "conversation": messages,  # full conversation history
        }

        return TaskClientOutput(output=TaskOutput(
            index=index,
            status=status,
            result=result_dict,
        ))

    def calculate_overall(self, results: List[TaskOutput]) -> JSONSerializable:
        statistics = {s: 0 for s in SampleStatus}
        for result in results:
            statistics[SampleStatus(result.status)] += 1
        for s in SampleStatus:
            statistics[s] /= len(results)
        statistics["average_history_length"] = sum(
            [len(result.history) for result in results]
        ) / len(results)
        statistics["max_history_length"] = max(
            [len(result.history) for result in results]
        )
        statistics["min_history_length"] = min(
            [len(result.history) for result in results]
        )
        ret = {
            "total": len(results),
            "validation": statistics,
        }
        res = requests.post(
            self.controller_address + "/calculate_overall",
            json=CalculateOverallRequest(name=self.name, results=results).dict(),
        )
        if res.status_code != 200:
            raise TaskNetworkException(res.text)
        ret["custom"] = res.json()
        return ret
