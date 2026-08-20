
sentence_end = [".", "!", "?", "...", "？", "。", "！"]
def combin_segment(segments, max_count):
    result = []
    current = None
    count = 0
    for seg in segments:
        text = seg["text"]
        if text is None:
            continue

        if current is None:
            current = {
                "text": text,
                "start": seg["start"],
                "end": seg["end"],
            }
            count = 1

        else:
            current["text"] += text
            current["end"] = seg["end"]
            count += 1

        if current["text"][-1] in sentence_end or count >= max_count:
            result.append(current)
            current = None
            count = 0

    # 最后一段不足 max_count 且没有句末标点
    if current is not None:
        result.append(current)

    return result


