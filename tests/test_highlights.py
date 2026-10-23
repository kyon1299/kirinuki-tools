from kirinuki.highlights import CHAT_LAG_SEC, pick_candidates, score_windows


def test_peak_becomes_candidate_without_overlap():
    n = 600
    total = [1] * n
    laugh = [0] * n
    for i in range(300, 320):
        total[i], laugh[i] = 20, 15
    counts = {"total": total, "laugh": laugh, "surprise": [0] * n}
    cands = pick_candidates(score_windows(counts), top_k=3, duration=n)
    assert cands
    best = max(cands, key=lambda c: c.score)
    # 盛り上がり(300〜320秒)からコメントの遅れ分を戻した場面が区間に入っている
    assert best.start <= 300 - CHAT_LAG_SEC <= best.end
    for a, b in zip(cands, cands[1:]):
        assert a.end <= b.start
