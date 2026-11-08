---
name: data-network-analyze
description: Graph and network analysis — similarity matrices, graph construction, community detection, centrality, and layman explanations of network metrics. Use when the user is asking about relationships between entities. Triggers on "network analysis", "graph analysis", "similarity matrix", "community detection", "centrality", "connected components", "who is connected to whom", "find clusters", "influence in network". Skip for raw SQL/schema only — use query-run; predictive ML models, which cct does not cover.
allowed-tools: "Bash(python3 *) Bash(uv *) Read Write"
user_invocable: true
metadata:
  version: 1.0.0
  author: calvindudek
---

# Network & Graph Analysis

Build, analyze, and explain networks from relational data. Every metric gets a plain-language explanation alongside the technical value.

## Prerequisites

| Dependency | Required | Install |
|------------|----------|---------|
| `networkx` | Yes | `uv add networkx` |
| `scipy` | Yes | `uv add scipy` |
| `matplotlib` | Yes | `uv add matplotlib` |
| `pandas` | Yes | `uv add pandas` |
| `scikit-learn` | Optional | `uv add scikit-learn` (for similarity matrices) |

## Core Workflow

### 1. Build the Network

**From relational data (edges):**
```python
import networkx as nx
import pandas as pd

# Example: co-attendance at events
edges = pd.read_csv("interactions.csv")  # columns: source, target, weight
G = nx.from_pandas_edgelist(edges, "source", "target", edge_attr="weight")
```

**From similarity matrix:**
```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Build similarity matrix from feature vectors
features = df[["feature1", "feature2", "feature3"]].values
sim_matrix = cosine_similarity(features)

# Convert to network (edges where similarity > threshold)
threshold = 0.7
G = nx.Graph()
for i in range(len(sim_matrix)):
    for j in range(i+1, len(sim_matrix)):
        if sim_matrix[i][j] > threshold:
            G.add_edge(df.index[i], df.index[j], weight=sim_matrix[i][j])
```

**Common use cases:**
- Co-appearance networks (which people appear at the same events?)
- Entity similarity (which companies have similar review profiles?)
- Content topic networks (which articles share tags/categories?)
- User behavior graphs (which users attend similar events?)

### 2. Network Statistics

Always compute and explain these metrics:

#### Graph-Level Stats

| Metric | Code | Layman explanation |
|--------|------|-------------------|
| Nodes | `G.number_of_nodes()` | "How many entities (people, companies, etc.) are in the network" |
| Edges | `G.number_of_edges()` | "How many connections exist between them" |
| Density | `nx.density(G)` | "What percentage of all possible connections actually exist. 0.05 means only 5% — a sparse network where most entities aren't directly connected" |
| Components | `nx.number_connected_components(G)` | "How many separate groups exist with no connections between them — like islands" |
| Avg clustering | `nx.average_clustering(G)` | "How much entities tend to form tight-knit groups. High (>0.5) means cliques; low (<0.1) means connections are spread out" |
| Avg path length | `nx.average_shortest_path_length(G)` (if connected) | "On average, how many hops to get from any entity to any other. Small (<4) means it's a 'small world'" |
| Diameter | `nx.diameter(G)` (if connected) | "The longest shortest path — the most separated pair of entities" |

#### Node-Level Metrics (Top-N)

| Metric | Code | Layman explanation |
|--------|------|-------------------|
| Degree | `dict(G.degree())` | "How many direct connections each entity has — the most connected people/companies" |
| Betweenness centrality | `nx.betweenness_centrality(G)` | "Who sits on the most paths between others — the bridges and brokers. Remove them and the network falls apart" |
| Closeness centrality | `nx.closeness_centrality(G)` | "Who can reach everyone else the fastest — the best-positioned entities" |
| Eigenvector centrality | `nx.eigenvector_centrality(G)` | "Who is connected to other well-connected entities — influence through association" |
| PageRank | `nx.pagerank(G)` | "Like Google's algorithm: who is important based on who links to them, weighted by the linker's own importance" |

**Always present as a ranked table with both the metric value and the plain-language meaning:**

```
Top 5 by Betweenness Centrality (bridge nodes):
1. Company X (0.342) — sits between 34% of all shortest paths; removing them would fragment the network
2. Company Y (0.218) — key connector between Cluster A and Cluster B
...
```

### 3. Community Detection

```python
from networkx.algorithms.community import louvain_communities, modularity

communities = louvain_communities(G, resolution=1.0)
mod = modularity(G, communities)
```

**Explain communities:**
- "The network naturally breaks into N clusters"
- For each cluster: "Cluster 1 (X members): dominated by [common trait]. Key members: [top 3 by degree within cluster]"
- Modularity score: "Modularity is 0.65 — this means the clusters are well-defined (>0.3 is good, >0.5 is strong structure)"

### 4. Similarity Matrices

**Building similarity matrices:**

| Method | Best for | Code |
|--------|----------|------|
| Cosine similarity | Text/feature vectors | `cosine_similarity(X)` |
| Jaccard similarity | Set overlap (tags, categories) | `1 - pdist(X, 'jaccard')` |
| Pearson correlation | Continuous features | `np.corrcoef(X)` |
| Co-occurrence | Event attendance, purchases | Custom: `(A.T @ A)` for binary matrix A |

**Always explain the similarity matrix:**
- "This is a square grid where each cell shows how similar two entities are"
- "1.0 = identical, 0.0 = nothing in common"
- "The diagonal is always 1.0 (everything is identical to itself)"
- Show the top-N most similar pairs and the top-N most dissimilar pairs

### 5. Visualization

```python
import matplotlib.pyplot as plt

# Color by community
colors = []
for node in G.nodes():
    for i, comm in enumerate(communities):
        if node in comm:
            colors.append(i)
            break

pos = nx.spring_layout(G, k=1/len(G)**0.5, iterations=50, seed=42)
plt.figure(figsize=(14, 10))
nx.draw_networkx(G, pos,
    node_color=colors, cmap=plt.cm.Set3,
    node_size=[G.degree(n) * 50 for n in G.nodes()],  # size by degree
    edge_color='#cccccc', alpha=0.8,
    font_size=8, with_labels=True)
plt.title("Network Graph — node size = connections, color = community")
plt.tight_layout()
plt.savefig("network.png", dpi=150, bbox_inches='tight')
```

**For large networks (>100 nodes):** Use `node_size` by degree, only label top-10 nodes, increase `k` for spacing.

### 6. Explanation Style

**Always pair every metric with a "so what":**

Bad: "Betweenness centrality of node X is 0.342"
Good: "Company X has a betweenness centrality of 0.342 — meaning 34% of all shortest paths between other companies pass through them. They're the key bridge in this network. If they left, several clusters would lose their connection to each other."

**For executives, lead with the story:**
1. "The network has N entities with M connections"
2. "It breaks into K natural clusters: [describe each in one sentence]"
3. "The most influential entities are: [top 3 with why]"
4. "The key bridges (removing them fragments the network): [top 3]"
5. "Interesting finding: [something non-obvious from the analysis]"

## Cross-Skill Awareness
- Expects prepared input (a table of nodes and edges); how to present the result: `references/presenting-results.md`
