def color_graph_greedy(variable_set, conflict_map, forced):
	colors = dict(forced) if forced else {}
	if forced:
		variable_set -= set(forced.keys())
	for v in variable_set:
		assert v not in colors
		existing = [colors[x] for x in conflict_map[v] if x in colors]
		colors[v] = min(x for x in range(len(existing) + 1) if x not in existing)
	return colors


def do_remap(mapping, remaps):
	for to_key, from_key in remaps.items():
		assert to_key not in mapping, "Duplicate: %s // %s" % (to_key, mapping)
		mapping[to_key] = mapping[from_key]
	return mapping


def color_graph(conflict_map, forced):
	remaps = {}
	# find any locations where the conflict map of one entry is a subset (inclusive) of another entry
	for k1, m1 in conflict_map.items():
		for k2, m2 in conflict_map.items():
			if k1 != k2 and m1.issubset(m2) and k1 not in m2 and k2 not in m1:
				remaps[k1] = k2
				break
	for ent in tuple(remaps):
		if ent not in remaps:
			continue
		if ent in forced:
			del remaps[ent]
			continue
		target = remaps[ent]
		recent = []
		while target in remaps and target not in recent:
			recent.append(target)
			target = remaps[target]
		remaps[ent] = target
		if target in recent:  # we've got a loop. kill the loop. (we can kill it anywhere and it'll fix the problem.)
			del remaps[target]
	for ent in remaps:
		assert remaps[ent] not in remaps
	remaining_variables = set(conflict_map.keys()) - set(remaps)
	remaining_forced = do_remap(dict(forced), remaps)
	colors = color_graph_greedy(remaining_variables, conflict_map, remaining_forced)
	do_remap(colors, remaps)
	return colors
