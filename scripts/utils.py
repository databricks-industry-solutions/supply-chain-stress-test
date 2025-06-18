import pandas as pd
import random, string, math
import matplotlib.pyplot as plt
from itertools import product
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pyomo.environ as pyo

def generate_data(N1: int=5, N2: int=10, N3: int=20) -> dict:
    """
    Generates a synthetic 3-tier network dataset for optimization.

    Parameters:
    N1 (int): Number of nodes in Tier 1.
    N2 (int): Number of nodes in Tier 2.
    N3 (int): Number of nodes in Tier 3.

    Returns:
    dict: A dictionary containing the generated dataset.
    """
    random.seed(777)  # DO NOT CHANGE! Keep topology reproducible

    # Ensure N3 is twice N2
    assert N3 == 2 * N2

    # Generate node names for each tier
    tier1 = [f"T1_{i}" for i in range(1, N1 + 1)]
    tier2 = [f"T2_{i}" for i in range(1, N2 + 1)]
    tier3 = [f"T3_{i}" for i in range(1, N3 + 1)]

    edges = []  # List to store edges (src, tgt)

    # Tier-2 → Tier-1 edges (1–3 edges out of each Tier-2)
    t2_out = {t2: set() for t2 in tier2}
    shuffled_t2 = tier2.copy()
    random.shuffle(shuffled_t2)
    for t1_node, t2_node in zip(tier1, shuffled_t2):
        edges.append((t2_node, t1_node))
        t2_out[t2_node].add(t1_node)

    for t2_node in tier2:
        desired = random.randint(1, 3)
        while len(t2_out[t2_node]) < desired:
            candidate = random.choice(tier1)
            if candidate not in t2_out[t2_node]:
                edges.append((t2_node, candidate))
                t2_out[t2_node].add(candidate)

    # Tier-3 → Tier-2 edges (exactly 1 edge per Tier-3)
    incoming_t2 = {t2: 0 for t2 in tier2}

    tier3_even = tier3[::2]
    for idx, t3_node in enumerate(tier3_even):
        tgt = tier2[idx]
        edges.append((t3_node, tgt))
        incoming_t2[tgt] += 1

    tier3_odd = tier3[1::2]
    for n, t3_node in enumerate(tier3_odd):
        low = n
        high = min(n + 1, N2 - 1)
        tgt = tier2[random.choice([low, high])] if low != high else tier2[low]
        edges.append((t3_node, tgt))
        incoming_t2[tgt] += 1

    # Generate material types and supplier material types
    n = math.ceil(len(tier2) / 3) + math.ceil(len(tier3) / 2)
    material_types = list(map(''.join, product(string.ascii_lowercase, repeat=3)))[:n]

    supplier_material_type = {}

    # 3 adjacent tier2 nodes produce the same material type
    for idx, node in enumerate(tier2):
        supplier_material_type[node] = material_types[math.floor(idx / 3)]

    # 2 adjacent tier3 nodes produce the same material type
    for idx, node in enumerate(tier3):
        supplier_material_type[node] = material_types[math.ceil(len(tier2) / 3) + math.floor(idx / 2)]

    # Nested sets N_minus, N_plus, P
    N_plus = defaultdict(set)  # i → list_of_children j
    N_minus = defaultdict(set)  # j → list_of_material_types k
    P = defaultdict(list)  # (j,k) → list_of_parents i

    for i, j in edges:
        if j in tier1 + tier2:
            N_minus[j].add(supplier_material_type[i])
    N_minus = {node: sorted(list(materials)) for node, materials in N_minus.items()}

    for i, j in edges:
        if i in tier2 + tier3:
            N_plus[i].add(j)
    N_plus = {node: sorted(list(childs)) for node, childs in N_plus.items()}

    for i, j in edges:
        if j in tier1 + tier2:
            P[(j, supplier_material_type[i])].append(i)

    # Scalar & tabular parameters
    rng_int = lambda lo, hi: random.randint(lo, hi)
    rng_float = lambda lo, hi, r=2: round(random.uniform(lo, hi), r)

    f = {j: rng_float(0.05, 0.30) for j in tier1}  # Profit margin for finished products
    s = {n: rng_int(1500, 3000) for n in tier1 + tier2 + tier3}  # On-hand inventory for every node
    d = {j: rng_int(500, 1000) for j in tier1}  # Demand per time unit for finished products
    c = {n: rng_int(1500, 3000) for n in tier1 + tier2 + tier3}  # Production capacity per time unit for every node

    r = {}
    for k in material_types:
        for j in tier1 + tier2:
            if k in N_minus[j]:
                r[(k, j)] = 1

    dataset = {
        "tier1": tier1,
        "tier2": tier2,
        "tier3": tier3,
        "edges": edges,
        "material_types": material_types,
        "supplier_material_type": supplier_material_type,
        "f": f,
        "s": s,
        "d": d,
        "c": c,
        "r": r,
        "N_minus": N_minus,
        "N_plus": N_plus,
        "P": P,
    }
    return dataset

def visualize_network(dataset: dict) -> None:
    """
    Visualizes the 3-tier network using matplotlib.

    Parameters:
    dataset dict: A dictionary containing the operational datas.
    """

    # Unpack the dataset
    tier1 = dataset["tier1"]
    tier2 = dataset["tier2"]
    tier3 = dataset["tier3"]
    edges = dataset["edges"]
    supplier_material_type = dataset["supplier_material_type"]

    # One distinct colour per code in the dict
    codes = sorted(set(supplier_material_type.values()))
    cmap = plt.get_cmap("tab20", len(codes))
    code_colour = {code: cmap(i) for i, code in enumerate(codes)}

    # Fallback for Tier-1 (or any node not in the dict)
    default_colour = "#9e9e9e"  # mid-grey

    # Helper that returns a list of colours in node order
    def colours_for(nodes):
        return [
            code_colour.get(supplier_material_type.get(n, None), default_colour)
            for n in nodes
        ]

    # POSITIONS (keep the centred, tier-specific gaps version)
    pos = {}

    gap_t1 = 3.0  # widest spacing
    gap_t2 = 2.2  # medium spacing
    gap_t3 = 1.5  # default spacing

    tier_specs = [  # (nodes , gap , y-coordinate)
        (tier1, gap_t1, 2),
        (tier2, gap_t2, 1),
        (tier3, gap_t3, 0),
    ]

    # Largest physical width among tiers (needed for centring)
    max_width = max((len(nodes) - 1) * gap for nodes, gap, _ in tier_specs)

    # Place each node
    for nodes, gap, y in tier_specs:
        width = (len(nodes) - 1) * gap
        x_offset = (max_width - width) / 2  # shift so tier is centred
        for idx, node in enumerate(nodes):
            pos[node] = (x_offset + idx * gap, y)

    # VISUALISATION
    fig, ax = plt.subplots(figsize=(15, 6))

    # Tier-1 (neutral grey)
    ax.scatter([pos[n][0] for n in tier1], [pos[n][1] for n in tier1],
               s=550, marker='o', c=colours_for(tier1),
               edgecolor='k', linewidth=0.5, label="Products")

    # Tier-2 (coloured by material-type)
    ax.scatter([pos[n][0] for n in tier2], [pos[n][1] for n in tier2],
               s=550, marker='s', c=colours_for(tier2),
               edgecolor='k', linewidth=0.5, label="Tier 2 (suppliers)")

    # Tier-3 (coloured by material-type)
    ax.scatter([pos[n][0] for n in tier3], [pos[n][1] for n in tier3],
               s=450, marker='^', c=colours_for(tier3),
               edgecolor='k', linewidth=0.5, label="Tier 3 (sub-suppliers)")

    # Node labels
    for node, (x, y) in pos.items():
        ax.text(x, y, node, ha='center', va='center', fontsize=8)

    # Directed edges
    for src, tgt in edges:
        sx, sy = pos[src]
        tx, ty = pos[tgt]
        ax.annotate("",
                    xy=(tx, ty), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>", lw=0.8))

    # Axes & title
    max_width = max((len(tier1) - 1) * 3.0, (len(tier2) - 1) * 2.2, (len(tier3) - 1) * 1.5)
    ax.set_xlim(-3.0, max_width + 3.0)
    ax.set_ylim(-0.7, 2.7)
    ax.axis("off")
    plt.title("Multi-Tier Supply Chain Network\n(colored by supplier_material_type)")

    # Custom legend: one patch per material-type code
    patches = [mpatches.Patch(color=code_colour[c], label=c) for c in codes]
    first_legend = ax.legend(handles=patches, title="supplier_material_type", fontsize=8,
                             title_fontsize=9, loc="upper left", bbox_to_anchor=(1.02, 1))
    # Add the tier legend underneath
    ax.legend(loc="upper left")
    ax.add_artist(first_legend)  # keep both legends

    plt.tight_layout()
    plt.show()

def build_and_solve_multi_tier_ttr(dataset: dict, disrupted: list[str], ttr: float, return_model: bool = False) -> pd.DataFrame:
    """
    Builds and solves a multi-tier TTR optimization model using Pyomo.

    Parameters:
    dataset (dict): The dataset generated by generate_data().
    disrupted (list): List of disrupted nodes in the scenario.
    ttr (float): Time to recover (TTR) for the disruption scenario.
    return_model (bool): Whether to return the solved Pyomo model.

    Returns:
    DataFrame
    """
    # Prepare your data
    data = {
        'V': dataset['tier1'],  # product nodes
        'D': dataset['tier1'] + dataset['tier2'],  # all BUT leaf nodes
        'U': dataset['tier2'] + dataset['tier3'],  # all BUT product nodes
        'K': dataset['material_types'],  # material types  (k ∈ 𝒩⁻(j))
        'S': disrupted,  # disrupted nodes in scenario n
        'N_minus': dataset['N_minus'],  # materials required to produce node j: dict  j ↦ list_of_k   (𝒩⁻(j))
        'N_plus': dataset['N_plus'],    # child nodes of node i: dict  i ↦ list_of_j   (𝒩⁺(i))
        'P': dataset['P'],  # parent nodes of node j of material type k: dict  (j,k) ↦ list_of_i  (𝒫_{jk})
        'f': dataset['f'],  # profit margin of 1 unit of j
        's': dataset['s'],  # inventory of i
        't': ttr,           # TTR for disruption scenario n (a scalar)
        'd': dataset['d'],  # demand for j per time unit
        'c': dataset['c'],  # plant capacity per time unit
        'r': dataset['r'],  # number of material type k needed for one unit of j 
    }

    # Build the ConcreteModel
    m = pyo.ConcreteModel()

    # Sets
    m.V = pyo.Set(initialize=data['V'])
    m.D = pyo.Set(initialize=data['D'])
    m.U = pyo.Set(initialize=data['U'])
    m.K = pyo.Set(initialize=data['K'])
    m.S = pyo.Set(initialize=data['S'])

    m.N_minus = pyo.Set(m.D, initialize=lambda mdl, j: data['N_minus'][j])
    m.N_plus = pyo.Set(m.U, initialize=lambda mdl, i: data['N_plus'][i])

    # Handy union of *all* nodes that may carry production volume
    m.NODES = pyo.Set(initialize=list(
        set(data['V']) | set(data['U'])
    ))

    # 𝒫_{jk} as map (j,k) → list_of_i
    m.P = pyo.Set(dimen=3, initialize=[
        (i, j, k)
        for (j, k), I in data['P'].items()
        for i in I
    ])

    # Parameters
    m.f = pyo.Param(m.V, initialize=data['f'], within=pyo.NonNegativeReals)
    m.s = pyo.Param(m.NODES, initialize=data['s'], within=pyo.NonNegativeIntegers)
    m.t = pyo.Param(initialize=data['t'], within=pyo.PositiveReals)
    m.d = pyo.Param(m.V, initialize=data['d'], within=pyo.NonNegativeIntegers)
    m.c = pyo.Param(m.NODES, initialize=data['c'], within=pyo.NonNegativeIntegers)
    m.r = pyo.Param(m.K, m.NODES, initialize=data['r'], within=pyo.NonNegativeReals)

    # Decision variables
    m.u = pyo.Var(m.NODES, domain=pyo.NonNegativeIntegers)  # production quantity of node i during time t
    m.l = pyo.Var(m.V, domain=pyo.NonNegativeIntegers)  # lost volume of product j during time t
    m.y_index = pyo.Set(within=m.U * m.NODES, initialize=lambda mdl: [
        (i, j) for i in mdl.U for j in mdl.N_plus[i]
    ]) # y is only needed for (i,j) pairs that actually make sense
    m.y = pyo.Var(m.y_index, domain=pyo.NonNegativeIntegers)  # allocation of upstream node i to downstream node j during time t

    # Objective
    def obj_rule(mdl):
        return sum(mdl.f[j] * mdl.l[j] for j in mdl.V)
    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    # Constraints
    # u_j − Σ_{i∈𝒫_{jk}} y_ij  ≤ 0,     ∀j∈𝒟, ∀k∈𝒩⁻(j)
    def bom_production_rule(mdl, j, k):
        rhs = sum(mdl.y[i, j] / mdl.r[k, j] for i in data['P'][(j, k)])
        return mdl.u[j] - rhs <= 0
    m.BomProduction = pyo.Constraint([(j, k) for j in m.D for k in m.N_minus[j]], rule=bom_production_rule)

    # Σ_{j∈𝒩⁺(i)} y_ij − u_i ≤ s_i,     ∀ i∈𝒰
    def flow_balance_rule(mdl, i):
        return sum(mdl.y[i, j] for j in mdl.N_plus[i]) - mdl.u[i] <= mdl.s[i]
    m.FlowBalance = pyo.Constraint(m.U, rule=flow_balance_rule)

    # u_j = 0,                           ∀ j∈𝒮⁽ⁿ⁾
    m.Disrupted = pyo.Constraint(m.S, rule=lambda m, j: m.u[j] == 0)

    # l_j + u_j + s_j ≥ d_j · t⁽ⁿ⁾,      ∀ j∈𝒱
    def demand_rule(mdl, j):
        return mdl.l[j] + mdl.u[j] + mdl.s[j] >= mdl.d[j] * mdl.t
    m.Demand = pyo.Constraint(m.V, rule=demand_rule)

    # u_j ≤ c_j · t⁽ⁿ⁾,        ∀ j∈NODES
    def capacity_rule(mdl, j):
        return mdl.u[j] <= mdl.c[j] * mdl.t
    m.Capacity = pyo.Constraint(m.NODES, rule=capacity_rule)

    # Solve
    solver = pyo.SolverFactory("highs")  # choose any LP/MIP solver that Pyomo can see (HiGHS, CBC, Gurobi, CPLEX, …)
    result = solver.solve(m, tee=False)

    if return_model:
        return pd.DataFrame(
        [[
            disrupted, 
            ttr, 
            result.solver.termination_condition, 
            pyo.value(m.OBJ), 
            m,
        ]], 
        columns=[
            "disrupted", 
            "ttr", 
            "termination_condition", 
            "lost_profit", 
            "model",
            ],
        )
    else:
        return pd.DataFrame(
            [[
                disrupted, 
                ttr, 
                result.solver.termination_condition, 
                pyo.value(m.OBJ),
            ]], 
            columns=[
                "disrupted", 
                "ttr", 
                "termination_condition", 
                "lost_profit", 
                ],
            )
        
def build_and_solve_multi_tier_tts(dataset: dict, disrupted: list[str], return_model: bool = False) -> pd.DataFrame:
    """
    Builds and solves a multi-tier TTS optimization model using Pyomo.

    Parameters:
    dataset (dict): The dataset generated by generate_data().
    disrupted (list): List of disrupted nodes in the scenario.
    return_model (bool): Whether to return the solved Pyomo model.

    Returns:
    DataFrame
    """
    # Prepare your data
    data = {
        'V': dataset['tier1'],  # product nodes
        'D': dataset['tier1'] + dataset['tier2'],  # all BUT leaf nodes
        'U': dataset['tier2'] + dataset['tier3'],  # all BUT product nodes
        'K': dataset['material_types'],  # material types  (k ∈ 𝒩⁻(j))
        'S': disrupted,  # disrupted nodes in scenario n
        'N_minus': dataset['N_minus'],  # materials required to produce node j: dict  j ↦ list_of_k   (𝒩⁻(j))
        'N_plus': dataset['N_plus'],  # child nodes of node i: dict  i ↦ list_of_j   (𝒩⁺(i))
        'P': dataset['P'],  # parent nodes of node j of material type k: dict  (j,k) ↦ list_of_i  (𝒫_{jk})
        's': dataset['s'],  # inventory of i
        'd': dataset['d'],  # demand for j per time unit
        'c': dataset['c'],  # plant capacity per time unit
        'r': dataset['r'],  # number of material type k needed for one unit of j 
    }

    # Build the ConcreteModel
    m = pyo.ConcreteModel()

    # Sets
    m.V = pyo.Set(initialize=data['V'])
    m.D = pyo.Set(initialize=data['D'])
    m.U = pyo.Set(initialize=data['U'])
    m.K = pyo.Set(initialize=data['K'])
    m.S = pyo.Set(initialize=data['S'])

    m.N_minus = pyo.Set(m.D, initialize=lambda mdl, j: data['N_minus'][j])
    m.N_plus = pyo.Set(m.U, initialize=lambda mdl, i: data['N_plus'][i])

    # Handy union of *all* nodes that may carry production volume
    m.NODES = pyo.Set(initialize=list(
        set(data['V']) | set(data['U'])
    ))

    # 𝒫_{jk} as map (j,k) → list_of_i
    m.P = pyo.Set(dimen=3, initialize=[
        (i, j, k)
        for (j, k), I in data['P'].items()
        for i in I
    ])

    # Parameters
    m.s = pyo.Param(m.NODES, initialize=data['s'], within=pyo.NonNegativeIntegers)
    m.d = pyo.Param(m.V, initialize=data['d'], within=pyo.NonNegativeIntegers)
    m.c = pyo.Param(m.NODES, initialize=data['c'], within=pyo.NonNegativeIntegers)
    m.r = pyo.Param(m.K, m.NODES, initialize=data['r'], within=pyo.NonNegativeReals)

    # Decision variables
    m.u = pyo.Var(m.NODES, domain=pyo.NonNegativeIntegers)  # production quantity of node i during time t
    m.y_index = pyo.Set(within=m.U * m.NODES, initialize=lambda mdl: [
        (i, j) for i in mdl.U for j in mdl.N_plus[i]
    ]) # y is only needed for (i,j) pairs that actually make sense
    m.y = pyo.Var(m.y_index, domain=pyo.NonNegativeIntegers) # allocation of upstream node i to downstream node j during time t
    m.t = pyo.Var(domain=pyo.PositiveReals)  # time to survive
    
    # Objective
    def obj_rule(mdl):
        return mdl.t
    m.OBJ = pyo.Objective(rule=obj_rule, sense=pyo.maximize)

    # Constraints
    # u_j − Σ_{i∈𝒫_{jk}} y_ij  ≤ 0,     ∀j∈𝒟, ∀k∈𝒩⁻(j)
    def bom_production_rule(mdl, j, k):
        rhs = sum(mdl.y[i, j] / mdl.r[k, j] for i in data['P'][(j, k)])
        return mdl.u[j] - rhs <= 0
    m.BomProduction = pyo.Constraint([(j, k) for j in m.D for k in m.N_minus[j]], rule=bom_production_rule)

    # Σ_{j∈𝒩⁺(i)} y_ij − u_i ≤ s_i,     ∀ i∈𝒰
    def flow_balance_rule(mdl, i):
        return sum(mdl.y[i, j] for j in mdl.N_plus[i]) - mdl.u[i] <= mdl.s[i]
    m.FlowBalance = pyo.Constraint(m.U, rule=flow_balance_rule)

    # u_j = 0,                           ∀ j∈𝒮⁽ⁿ⁾
    m.Disrupted = pyo.Constraint(m.S, rule=lambda m, j: m.u[j] == 0)

    # u_j + s_j ≥ d_j · t⁽ⁿ⁾,      ∀ j∈𝒱
    def demand_rule(mdl, j):
        return mdl.u[j] + mdl.s[j] >= mdl.d[j] * mdl.t
    m.Demand = pyo.Constraint(m.V, rule=demand_rule)

    # u_j ≤ c_j · t⁽ⁿ⁾,        ∀ j∈NODES
    def capacity_rule(mdl, j):
        return mdl.u[j] <= mdl.c[j] * mdl.t
    m.Capacity = pyo.Constraint(m.NODES, rule=capacity_rule)

    # Solve
    solver = pyo.SolverFactory("highs")  # choose any LP/MIP solver that Pyomo can see (HiGHS, CBC, Gurobi, CPLEX, …)
    result = solver.solve(m, tee=False)

    if return_model:
        return pd.DataFrame(
        [[
            disrupted,
            result.solver.termination_condition, 
            pyo.value(m.OBJ), 
            m,
        ]], 
        columns=[
            "disrupted", 
            "termination_condition", 
            "tts", 
            "model",
            ],
        )
    else:
        return pd.DataFrame(
            [[
                disrupted, 
                result.solver.termination_condition, 
                pyo.value(m.OBJ),
            ]], 
            columns=[
                "disrupted", 
                "termination_condition", 
                "tts", 
                ],
            )
    
    