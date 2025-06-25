import numpy as np
from random import random
from math import log2

import heapq
import json

class HNSW:
    def cosine_distance(self, a, b):
        return np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b)

    def __init__(self, m=5, ef=10):
        self.distance = self.cosine_distance
        self.m = m
        self.ef = ef
        self.level_multiplier = 1/log2(m)
        self.probs = self.gen_prob()
        self.n_levels = len(self.probs)
        self.graph = [{} for _ in range(self.n_levels)]
        self.entry_point = None
        self.entry_lvl = None
        self.emb = {}

    def gen_prob(self):
        level = 0
        probs = []
        while True:
            prob = 1/np.exp(level/self.level_multiplier) * (1-1/np.exp(1/self.level_multiplier))
            if prob < 1e-9:
                break
            probs.append(prob)
            level += 1
        return probs

    def assign_level(self):
        rn = random()
        # print(rn)
        for level in range(self.n_levels):
            if rn < self.probs[level]:
                return level
            rn -= self.probs[level]
        return level

    def add(self, query_id, query_vec):
        self.emb[query_id] = query_vec

        ep = self.entry_point
        level = self.assign_level()+1
        # print(f"add node {query_id} to level {level}")
        for i in range(level):
            self.graph[i].update({query_id: {}})

        counter = 0
        if self.entry_point is not None:
            sim = self.distance(self.emb[ep],query_vec)
            for lvl in range(self.entry_lvl-1, level-1, -1):   
                ep, sim, cnt = self.search_nearest(query_vec, ep, sim, lvl)
                counter += cnt
            # now ep is the nearest node at the level of insertion
            # we insert the query node by making k connections at that lvl
            candidates = [(sim, ep)]
            for lvl in range(min(self.entry_lvl,level)-1, -1, -1):
                k = self.m if lvl>0 else 2*self.m
                candidates, cnt = self.find_nearest_k(query_vec, candidates, lvl, k)
                counter += cnt
                layer = self.graph[lvl]
                for sim, node in candidates:
                    layer[query_id][node] = sim
                    layer[node][query_id] = sim
                # next level will start with k candidates already
                # it will explore the lower layer to find an update 
                # k candidates
        if not self.entry_lvl or level > self.entry_lvl:
            self.entry_point = query_id
            self.entry_lvl = level
            print(f"update entry node to {query_id} at lvl {level}")
        # print(f"{query_id} visited {counter} nodes")

    def search_nearest(self, qvec, start, start_sim, lvl):
        nearest = start
        closest_sim = -start_sim
        queue = [(-start_sim, start)]
        graph = self.graph[lvl]
        # print(f"lvl {lvl}: {graph}")
        visited = set([start])
        i = 0
        while queue:
            i += 1
            sim, node = heapq.heappop(queue)
            nbs = [x for x in graph[node] if x not in visited]
            visited.update(nbs)
            sims = [self.distance(qvec, self.emb[nb]) for nb in nbs]
            for nb, sim in zip(nbs, sims):
                if -sim < closest_sim:
                    nearest = nb
                    closest_sim = sim
                    heapq.heappush(queue, (-sim, nb))
        return nearest, -closest_sim, i

    def find_nearest_k(self, qvec, candidates, lvl, k, filtered_ids=None):
        # nearest_k we want to pop the largest in the list
        # so we maintain the k smallest 
        nearest_k = [(sim, node) for sim, node in candidates if not filtered_ids or node in filtered_ids]
        candidates = [(-sim, node) for sim, node in candidates]
        graph = self.graph[lvl]
        visited = set([node for sim, node in candidates])
        i = 0
        while candidates:
            sim, node = heapq.heappop(candidates)
            i += 1
            nbs = [x for x in graph[node] if x not in visited]
            visited.update(nbs)
            sims = [self.distance(qvec, self.emb[nb]) for nb in nbs]
            for nb, sim in zip(nbs, sims):
                if len(nearest_k) < k:
                    heapq.heappush(candidates, (-sim, nb))
                    if filtered_ids:
                        if nb not in filtered_ids:
                            continue
                    heapq.heappush(nearest_k, (sim, nb))
                elif nearest_k[0][0] < sim:
                    # replace biggest item in the queue
                    heapq.heappush(candidates, (-sim, nb))
                    if filtered_ids:
                        if nb not in filtered_ids:
                            continue
                    heapq.heapreplace(nearest_k, (sim,nb))
        # nearest_k = [(sim, node) for sim, node in nearest_k]
        return nearest_k, i

    def search(self, qvec, k=1, filter_ids=None):
        ep = self.entry_point
        sim = self.distance(self.emb[ep], qvec)

        counter = 0
        for lvl in range(self.entry_lvl-1, 0, -1):
            ep, sim, cnt = self.search_nearest(qvec, ep, sim, lvl)
            counter += cnt
        print(f"searched {counter}")
        # get top k from level 0
        if filter_ids:
            filter_ids = set(filter_ids)
        top_k_nodes, _ = self.find_nearest_k(qvec, [(sim, ep)], 0, k, filter_ids)
        top_k_nodes.sort(reverse=True)
        return top_k_nodes

    def save(self, filename="hnsw.json"):
        with open(filename, "w") as f:
            json.dump({
                "graph": self.graph,
                "emb": {k: v.tolist() for k, v in self.emb.items()},
                "entry_point": self.entry_point,
                "entry_lvl": self.entry_lvl,
                "m": self.m,
                "ef": self.ef,
                "probs": self.probs,
                "level_multiplier": self.level_multiplier
            }, f)
        print(f"HNSW object saved to {filename}")
    
    @classmethod
    def load(cls, filename="hnsw.json"):
        with open(filename, "r") as f:
            data = json.load(f)
            instance = cls(m=data["m"], ef=data["ef"])
            instance.graph = data["graph"]
            instance.emb = {k: np.array(v) for k, v in data["emb"].items()}
            instance.entry_point = data["entry_point"]
            instance.entry_lvl = data["entry_lvl"]
            instance.probs = data["probs"]
            instance.level_multiplier = data["level_multiplier"]
        print(f"loaded HNSW object from {filename}")
        return instance


if __name__=="__main__":
    hnsw = HNSW(5)

    # data = np.array(np.float32(np.random.random((1000, 32))))
    # for idx, vec in enumerate(data):
    #     hnsw.add(idx, vec)
    import json
    data = []
    # with open("local_data/coffee_EC_embeddings.txt") as f:
    #     for line in f:
    #         place = json.loads(line)
    #         id = place['place_id']
    #         vec = np.array(place['embedding'])
    #         data.append((id, vec))
    #         hnsw.add(id, vec)
    #         if id == "08f194ad32d5600b035cc9620a94d371":
    #             qvec = vec
                
    # hnsw.save()
    hnsw = HNSW.load()
    qvec = hnsw.emb['08f194ad32d5600b035cc9620a94d371']
    print(qvec)
    print(len(qvec))
    
    print(hnsw.probs)
    for idx, layer in enumerate(hnsw.graph):
        print(idx, len(layer))
        if len(layer)==0:
            break

    # qvec = np.float32(np.random.random((32)))
    filter_ids = ['08f194ad32d5600b035cc9620a94d371']
    nearest_nodes = hnsw.search(qvec, 5, filter_ids )
    print(nearest_nodes)

    # brute force
    queue = []
    for idx, vec in data:
        sim = hnsw.distance(qvec, vec)
        heapq.heappush(queue, (-sim, idx))

    print(heapq.nsmallest(5, queue))