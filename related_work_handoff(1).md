# Related Work 交接

Hunter Zhang | Section 2 Related Work 改完了，按下面三步操作即可。

---

## 步骤 1：替换 `acl_latex.tex` 里的 Related Work

打开 `acl_latex.tex`，找到 `\section{Related Work}`（约第 114 行），把这一行**到 `\section{Method}` 之前**的所有内容删掉，粘贴下面这段：

```latex
\section{Related Work}
% 0.5-1 page

The evaluation and improvement of LLM-based agents on interactive tasks
has advanced along three closely related lines: benchmark construction,
reasoning-and-acting interaction paradigms, and inference-only improvement
strategies based on prompting and memory. However, existing work does not
fully characterize which inference-only interventions mitigate specific
failure modes in operating system task execution.

\paragraph{Benchmarks for web and digital agents.}
\citet{deng2023mind2web} introduced a large-scale generalist web agent
benchmark with 2,350 tasks across 137 real-world websites. Even GPT-4
achieves only approximately 36\% step success rate under in-context
learning, showing that generalization to unseen digital environments remains
difficult. \citet{zhou2023webarena} addressed the limitation of offline web
evaluation by deploying self-hosted, fully functional websites in
reproducible Docker containers and evaluating agents through programmatic
state inspection rather than action-sequence matching. The best GPT-4-based
agent in WebArena achieves only 14.41\% success, far below the 78.24\%
human baseline, indicating that live digital environments remain challenging
even for frontier models. \citet{liu2023agentbench} extends this benchmark
perspective to a broader set of environments, including the operating system
domain that is the focus of our replication.

\paragraph{Reasoning and acting paradigms.}
\citet{yao2022react} introduced ReAct, a reasoning-and-acting framework that
interleaves free-form ``thought'' tokens with environment actions. This
format gives the agent an implicit working memory without parameter updates
and has become a useful conceptual template for later agent frameworks.
However, ReAct also reveals a characteristic failure mode: repetitive
thought--action loops account for 47\% of its failures on HotpotQA. This
finding motivates stronger inference-time interventions such as
self-reflection, memory augmentation, and explicit planning. Whether similar
dominant failure modes appear in OS task execution remains an empirical
question, especially because shell commands are syntactically rigid and can
irreversibly alter environment state.

\paragraph{Prompt-based and memory-augmented agent improvement.}
A complementary line of work improves LLM agents without updating model
parameters. \citet{shinn2023reflexion} propose Reflexion, which augments
ReAct with a verbal self-reflection step: after a failed trajectory, the
agent writes a natural-language critique and stores it in an episodic memory
buffer that conditions later attempts. \citet{madaan2023selfrefine} develop
Self-Refine, where a single LLM iteratively generates, critiques, and
revises its own output without supervised training or reinforcement
learning. \citet{erdogan2025plan} take an architectural approach through
PLAN-AND-ACT, decomposing the agent into a \textsc{Planner} that produces
structured plans and an \textsc{Executor} that grounds them into actions. A
central finding is that even an untrained \textsc{Executor} improves by 34
percentage points on WebArena-Lite when paired with a high-quality
\textsc{Planner}, suggesting that plan quality can be a major bottleneck for
current LLM-based agents.

\paragraph{Position of our work.}
Together, these works provide the benchmark, interaction, and inference-time
improvement foundations for our study. Building on the OS domain of
\citet{liu2023agentbench}, our work examines not only whether prompt- and
memory-based interventions improve task success, but also which categories
of failure they actually mitigate in shell command execution.
```

---

## 步骤 2：在 `custom.bib` 末尾追加两条 bib

打开 `custom.bib`，滚到文件末尾，粘贴：

```bibtex
@inproceedings{shinn2023reflexion,
  title     = {Reflexion: Language Agents with Verbal Reinforcement Learning},
  author    = {Shinn, Noah and Cassano, Federico and Berman, Edward and
               Gopinath, Ashwin and Narasimhan, Karthik and Yao, Shunyu},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {36},
  year      = {2023}
}

@inproceedings{madaan2023selfrefine,
  title     = {Self-Refine: Iterative Refinement with Self-Feedback},
  author    = {Madaan, Aman and Tandon, Niket and Gupta, Prakhar and
               Hallinan, Skyler and Gao, Luyu and Wiegreffe, Sarah and
               Alon, Uri and Dziri, Nouha and Prabhumoye, Shrimai and
               Yang, Yiming and Gupta, Shashank and
               Majumder, Bodhisattwa Prasad and Hermann, Katherine and
               Welleck, Sean and Yazdanbakhsh, Amir and Clark, Peter},
  booktitle = {Advances in Neural Information Processing Systems},
  volume    = {36},
  year      = {2023}
}
```

---

## 步骤 3：从 `custom.bib` 删掉 `chen2025reinforcement` 条目

新版 Related Work 不再引用这篇，把整条删掉：

```bibtex
@article{chen2025reinforcement,
  title={Reinforcement learning for long-horizon interactive llm agents},
  author={Chen, Kevin and Cusumano-Towner, Marco and Huval, Brody and Petrenko, Aleksei and Hamburger, Jackson and Koltun, Vladlen and Kr{\"a}henb{\"u}hl, Philipp},
  journal={arXiv preprint arXiv:2502.01600},
  year={2025}
}
```
