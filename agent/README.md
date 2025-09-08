<img src=https://raw.githubusercontent.com/databricks-industry-solutions/.github/main/profile/solacc_logo.png width="600px">

[![Databricks](https://img.shields.io/badge/Databricks-Solution_Accelerator-FF3621?style=for-the-badge&logo=databricks)](https://databricks.com)
[![Unity Catalog](https://img.shields.io/badge/Unity_Catalog-Enabled-00A1C9?style=for-the-badge)](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
[![DBR](https://img.shields.io/badge/DBR-CHANGE_ME-red?logo=databricks&style=for-the-badge)](https://docs.databricks.com/release-notes/runtime/CHANGE_ME.html)

## Business Problem
Efficiently managing supply chains has long been the top priority for retail, consumer goods, and manufacturing companies. This has become even more critical today as disruptions and uncertainties in supply chain networks continue to increase. Supply chain managers are increasingly adopting data driven approaches to maintain efficient logistics and quickly address issues that arise during operations. These approaches rely on collecting operational data from the supply chain network and typically integrate optimization techniques, often with mathematical models, at their core.

The advantage of data driven solutions is that they enable faster, more accurate, and scalable supply chain decisions compared to manual methods based on experience and intuition, which are often constrained by bias and the inability to scale. However, this comes at a cost, as it requires experts trained in mathematical modeling who also possess business domain knowledge. These modeling experts translate business requirements from business planners into a set of parameters, run the optimization tools, and interpret the results in a business friendly manner. This is a time consuming process, and such talent is extremely difficult to find. As a result, this remains one of the biggest challenges preventing many companies from bringing data driven solutions in supply chain management to life.

With the rise of large language models and agents, however, the narrative is beginning to change. Recently, David Simchi-Levi, a well-known MIT professor in supply chain and inventory management, together with a Microsoft Research team, published a [paper](https://arxiv.org/abs/2507.21502) advocating the use of large language models as agents to bridge the gap between business and optimization tools. The authors suggest that an agentic system with access to supply chain data and mathematical optimization tools can be engaged in much the same way as we interact with modeling experts today—an approach that democratizes supply chain technologies.

From an AI engineer's perspective, this approach has great value for grounding responses and providing explanations. Although progress has been rapid, large language models are still prone to hallucination. Techniques such as retrieval augmented generation and fine tuning are commonly used to reduce this risk. Mathematical optimization, on the other hand, is a fully transparent and explainable technique that can generate concrete and actionable plans. Allowing a large language model to access this technique as a tool and interpret the outcomes greatly reduces the risk of hallucination, which is critical for building trust with business stakeholders.

The solution accelerator demonstrates how to build, evaluate and deploy such an agentic system on Databricks.

## Reference Architecture

## Authors

<ryuta.yoshimatsu@databricks.com>, <puneet.jain@databricks.com>

## Project support 

Please note the code in this project is provided for your exploration only, and are not formally supported by Databricks with Service Level Agreements (SLAs). They are provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of these projects. The source in this project is provided subject to the Databricks [License](./LICENSE.md). All included or referenced third party libraries are subject to the licenses set forth below.

Any issues discovered through the use of this project should be filed as GitHub Issues on the Repo. They will be reviewed as time permits, but there are no formal SLAs for support. 

## License

&copy; 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the Databricks License [https://databricks.com/db-license-source].  All included or referenced third party libraries are subject to the licenses set forth below.

| library                                | description             | license    | source                                              |
|----------------------------------------|-------------------------|------------|-----------------------------------------------------|
| pyomo | An object-oriented algebraic modeling language in Python for structured optimization problems | BSD-3 | https://pypi.org/project/pyomo/
| highspy | Linear optimization solver (HiGHS) | MIT | https://pypi.org/project/highspy/
