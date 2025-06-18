<img src=https://raw.githubusercontent.com/databricks-industry-solutions/.github/main/profile/solacc_logo.png width="600px">

[![DBR](https://img.shields.io/badge/DBR-CHANGE_ME-red?logo=databricks&style=for-the-badge)](https://docs.databricks.com/release-notes/runtime/CHANGE_ME.html)
[![CLOUD](https://img.shields.io/badge/CLOUD-CHANGE_ME-blue?logo=googlecloud&style=for-the-badge)](https://databricks.com/try-databricks)

## Business Problem

Global disruptions from pandemics, wars, and climate events have exposed vulnerabilities in supply chains—resulting in shortages, cost spikes, and reputational damage. Building resilient supply chains enables companies to maintain service levels, capture market share when competitors falter and protect revenue, margins, and brand credibility during crises.

Stress testing simulates extreme but plausible shocks—such as supplier failures, port closures, or demand surges—to reveal hidden risks and single points of failure. By quantifying the financial impact, organizations can prioritize mitigation strategies, diversify sourcing, build targeted inventory buffers, and implement agile decision rules—strengthening adaptability in the face of uncertainty.

This solution accelerator implements the methodology proposed in a [paper](https://dspace.mit.edu/handle/1721.1/101782), which applies stress testing to supply chain networks using digital twins—virtual models constructed from real operational data. Simulating a wide range of disruption scenarios allows businesses to assess potential impacts, identify vulnerabilities, and make proactive, informed decisions.

At the core of this approach is a linear optimization problem, where we optimize the network configuration toward a common objective subject to a set of constraints. This accelerator uses [Pyomo](https://pyomo.readthedocs.io/en/stable/index.html) and [HiGHS](https://github.com/ERGO-Code/HiGHS) to model and solve the optimization problem, and leverages [Ray](https://docs.databricks.com/aws/en/machine-learning/ray/) to scale the process across thousands of simulations.

Databricks is the ideal platform for building this solution. Key advantages include:

1. **Delta Sharing** – Access to up-to-date operational data is vital for resilient supply chain solutions. Delta Sharing enables seamless data exchange between retailers and suppliers—even if one party isn't using Databricks.

2. **Scalability** – Running linear optimization across networks with thousands of nodes and simulating thousands of disruption scenarios is computationally demanding. Databricks provides horizontal scalability to handle these workloads efficiently.

3. **Open Standards** – Databricks integrates smoothly with open-source and third-party tools, allowing teams to use familiar libraries with minimal friction. This flexibility supports custom modeling of business problems and ensures transparency for auditability, validation, and ongoing refinement.


## Reference Architecture

<img src='images/cartoon.png' width=650>

## Authors

<ryuta.yoshimatsu@databricks.com>,  <luis.herrera@databricks.com>, <puneet.jain@databricks.com>

## Project support 

Please note the code in this project is provided for your exploration only, and are not formally supported by Databricks with Service Level Agreements (SLAs). They are provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of these projects. The source in this project is provided subject to the Databricks [License](./LICENSE.md). All included or referenced third party libraries are subject to the licenses set forth below.

Any issues discovered through the use of this project should be filed as GitHub Issues on the Repo. They will be reviewed as time permits, but there are no formal SLAs for support. 

## License

&copy; 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the Databricks License [https://databricks.com/db-license-source].  All included or referenced third party libraries are subject to the licenses set forth below.

| library                                | description             | license    | source                                              |
|----------------------------------------|-------------------------|------------|-----------------------------------------------------|
| pyomo | An object-oriented algebraic modeling language in Python for structured optimization problems | BSD | https://pypi.org/project/pyomo/
| highspy | Linear optimization solver (HiGHS) | MIT | https://pypi.org/project/highspy/
| ray | Framework for scaling AI/Python applications | Apache 2.0 | https://github.com/ray-project/ray