# storage/disk.py  — Disk Scheduling algorithms (ported from diskSched.py)

def build_steps(head, queue, direction, disk, algo):
    """
    Returns a list of step dicts: {"from", "to", "note", optional "jump": True}
    Exactly the same logic as CODE 2 (diskSched.py).
    """
    result = []
    remaining = list(queue)
    pos = head

    if algo == "fcfs":
        for t in queue:
            result.append({"from": pos, "to": t, "note": f"Service track {t}"})
            pos = t

    elif algo == "sstf":
        while remaining:
            closest = min(remaining, key=lambda t: abs(t - pos))
            result.append({"from": pos, "to": closest,
                            "note": f"Closest: track {closest} (dist {abs(closest - pos)})"})
            pos = closest
            remaining.remove(closest)

    elif algo == "scan":
        sorted_q = sorted(remaining)
        go_up = (direction == "up")
        if not go_up:
            left  = list(reversed([t for t in sorted_q if t <= pos]))
            right = [t for t in sorted_q if t > pos]
            if left:
                result.append({"from": pos, "to": left[0], "note": "Moving toward track 0"})
            cur = left[0] if left else pos
            for t in left[1:]:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
            result.append({"from": cur, "to": 0, "note": "Reach end (track 0), reverse direction"}); cur = 0
            for t in right:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
        else:
            right = [t for t in sorted_q if t >= pos]
            left  = list(reversed([t for t in sorted_q if t < pos]))
            if right:
                result.append({"from": pos, "to": right[0], "note": "Moving toward higher tracks"})
            cur = right[0] if right else pos
            for t in right[1:]:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
            end = disk - 1
            result.append({"from": cur, "to": end, "note": f"Reach end (track {end}), reverse direction"}); cur = end
            for t in left:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t

    elif algo == "cscan":
        sorted_q = sorted(remaining)
        right = [t for t in sorted_q if t >= pos]
        left  = [t for t in sorted_q if t < pos]
        cur = pos
        for t in right:
            result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
        end = disk - 1
        result.append({"from": cur, "to": end, "note": f"Reach end (track {end})"}); cur = end
        result.append({"from": cur, "to": 0, "note": "Jump back to track 0 (no service)", "jump": True}); cur = 0
        for t in left:
            result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t

    elif algo == "look":
        sorted_q = sorted(remaining)
        go_up = (direction == "up")
        if not go_up:
            left  = list(reversed([t for t in sorted_q if t <= pos]))
            right = [t for t in sorted_q if t > pos]
            cur = pos
            for t in left:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
            if right:
                result.append({"from": cur, "to": right[0],
                                "note": f"No more requests left, reverse — service track {right[0]}"}); cur = right[0]
            for t in right[1:]:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
        else:
            right = [t for t in sorted_q if t >= pos]
            left  = list(reversed([t for t in sorted_q if t < pos]))
            cur = pos
            for t in right:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
            if left:
                result.append({"from": cur, "to": left[0],
                                "note": f"No more requests ahead, reverse — service track {left[0]}"}); cur = left[0]
            for t in left[1:]:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t

    elif algo == "clook":
        sorted_q = sorted(remaining)
        right = [t for t in sorted_q if t >= pos]
        left  = [t for t in sorted_q if t < pos]
        cur = pos
        for t in right:
            result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t
        if left:
            result.append({"from": cur, "to": left[0],
                            "note": f"Jump to lowest request track {left[0]} (no service)", "jump": True}); cur = left[0]
            for t in left[1:]:
                result.append({"from": cur, "to": t, "note": f"Service track {t}"}); cur = t

    return result
