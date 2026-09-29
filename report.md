# Project 1 Report: Intelligent Search Visualizer

> [!IMPORTANT]
> **AUTOGRADER COMPLIANCE INSTRUCTIONS:**
> This report is parsed automatically by the autograder. To ensure you receive full credit for your work:
> 1. **Do not modify** the section headers (`## ...`) or bold field keys (e.g., `**Name:**`, `**Selected Region:**`, `**Live Deployment URL:**`, etc.).
> 2. **Write your answers directly after** the colon `:` of each field, replacing the placeholder text completely (including the outer brackets `[` and `]`).
> 3. **Maintain the file structure**. Changing headers, bold titles, or deleting lines can cause the autograder to miss your responses and award 0 marks.

---

## Student Information 
- **Name:** Anirudh Gupta
- **UID (netID):** agupt101
- **UIN:** 655406023

---

## Section 1: Selected City Region
- **Selected Region:** California, USA

---

## Section 2: Map Graph Configuration
- **Total Cities Configured:** 25
- **Total Connection Edges:** 40
- **Graph Fully Connected:** Yes

---

## Section 3: Local Verification & Search Algorithms
*Check the algorithms you successfully ran and verified on your local development server by placing an `x` in the brackets (e.g., `[x]`):*
- [x] Breadth-First Search (BFS)
- [x] Depth-First Search (DFS)
- [x] Uniform Cost Search (UCS)
- [x] Iterative Deepening Search (IDS)
- [x] Greedy Best-First Search (Greedy)
- [x] A* Search (A*)

---

## Section 4: Deployed and Presentation Information
- **Deployment Platform:** Render
- **Live Deployment URL:** https://cs-411.onrender.com
- **Video Presentation Link:** https://drive.google.com/file/d/1_3muLQaVABzHWjacp0Bgj9bP9fvWLZ_N/view?usp=drive_link

---

## Section 5: Discussion
- **Which search algorithm is best for this route finding problem?** 
    A* is the best choice. The goal is the shortest drive, and edge costs are real OSRM road distances in miles, so the path with the fewest roads is often not the path with the fewest miles. Only UCS and A* are guaranteed to return the minimum-mile route, and A* gets there while expanding fewer cities because its heuristic (straight-line haversine distance to the goal, computed from the Nominatim coordinates) points the search toward the destination. That heuristic is admissible because no road between two cities can be shorter than the straight line between them, and it is consistent because it obeys the triangle inequality with the road edges, so A* stays optimal even with an explored set. BFS and IDS minimize the number of road segments, not miles, so they only return the shortest drive when the two happen to match. DFS returns whatever path it reaches first and can be far longer than necessary. Greedy Best-First is the fastest to reach the goal but ignores the miles already driven, so it can be pulled into a detour that looks close in a straight line but is longer by road.
- **Search Efficiency (Nodes expanded/time taken comparison):** 
    I compared the algorithms by running each one on the same start and goal in the app, recording the nodes expanded shown on the page and the runtime (time_ms) returned by the /api/search endpoint. Greedy expanded the fewest nodes, because it heads straight at the goal, but it does not always return the cheapest route. A* expanded fewer nodes than UCS in my tests while returning the same optimal cost, since h(n) lets it skip cities that point away from the goal. UCS explores outward in every direction in order of miles driven, so it expands more nodes than A* to find the same route. BFS and DFS sit in between; DFS can expand few nodes when its alphabetical ordering happens to lead toward the goal, but its path is usually longer. IDS expanded by far the most nodes, often ten times more than BFS or more, because every new depth limit restarts the search and re-expands all the shallower cities; that repeated work is the cost of keeping memory as low as DFS. All six ran in well under a millisecond on this 25-city graph, so runtime differences are small in absolute terms, but nodes expanded shows how the work would scale on a real road network with millions of intersections, where A*'s savings over UCS would matter a lot.
- **Link the idea of search algorithm to today Generative AI.** 
    Large language models generate text one token at a time, and choosing the output is a search problem over a huge tree where each state is the text so far and each action appends a token. Greedy decoding always takes the single most likely next token, which is the same idea as Greedy Best-First Search: fast, but it can commit early to a path that turns out worse overall. Beam search keeps the best k partial sequences at each step, which is like a memory-limited best-first search that trades optimality for bounded memory. Newer reasoning systems go further: tree-of-thought style methods expand several candidate reasoning steps, score them with a value model or verifier that acts like a heuristic h(n), and expand the most promising ones first, which is close to A* or best-first search over reasoning steps. Game-playing systems like AlphaGo combine Monte Carlo tree search with a learned policy and value network, the same "path cost plus estimated remaining value" idea as A*, with the heuristic learned from data instead of computed from geometry. The main lesson carries over from this project: a good heuristic lets the search spend its compute on promising branches instead of expanding everything.