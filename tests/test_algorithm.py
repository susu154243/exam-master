"""
FSRS 间隔重复算法单元测试

覆盖核心函数的语义正确性验证：
- get_retrievability(): 保留率公式
- get_interval(): 间隔计算
- update_stability(): 稳定性更新
- update_difficulty(): 难度更新
- fsrs_schedule(): 端到端调度
- predict_review_load(): 复习负载预测
"""
import pytest
import sys
import os
from datetime import datetime, timedelta

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    get_retrievability,
    get_interval,
    update_stability,
    update_difficulty,
    fsrs_schedule,
    init_memory_state,
    predict_review_load,
)


class TestGetRetrievability:
    """保留率公式测试"""

    def test_retrievability_at_stability(self):
        """当 delta_t == stability 时，R 应等于 0.9"""
        stability = 10.0
        delta_t = 10.0
        r = get_retrievability(stability, delta_t)
        assert abs(r - 0.9) < 0.001, f"R(S, S) 应为 0.9，实际为 {r}"

    def test_retrievability_before_stability(self):
        """当 delta_t < stability 时，R 应大于 0.9"""
        stability = 10.0
        delta_t = 5.0
        r = get_retrievability(stability, delta_t)
        assert r > 0.9, f"R(S/2, S) 应 > 0.9，实际为 {r}"
        assert r < 1.0, f"R(S/2, S) 应 < 1.0，实际为 {r}"

    def test_retrievability_after_stability(self):
        """当 delta_t > stability 时，R 应小于 0.9"""
        stability = 10.0
        delta_t = 20.0
        r = get_retrievability(stability, delta_t)
        assert r < 0.9, f"R(2S, S) 应 < 0.9，实际为 {r}"
        assert r > 0.0, f"R(2S, S) 应 > 0，实际为 {r}"

    def test_retrievability_zero_delta_t(self):
        """当 delta_t == 0 时，R 应等于 1.0"""
        stability = 10.0
        delta_t = 0.0
        r = get_retrievability(stability, delta_t)
        assert r == 1.0, f"R(0, S) 应为 1.0，实际为 {r}"

    def test_retrievability_negative_delta_t(self):
        """当 delta_t < 0 时，R 应返回 1.0（防御性处理）"""
        stability = 10.0
        delta_t = -5.0
        r = get_retrievability(stability, delta_t)
        assert r == 1.0, f"R(-5, S) 应为 1.0，实际为 {r}"

    def test_retrievability_zero_stability(self):
        """当 stability == 0 时，R 应返回 1.0（防御性处理）"""
        stability = 0.0
        delta_t = 5.0
        r = get_retrievability(stability, delta_t)
        assert r == 1.0, f"R(t, 0) 应为 1.0，实际为 {r}"

    def test_retrievability_monotonic_decrease(self):
        """保留率应随时间单调递减"""
        stability = 10.0
        r1 = get_retrievability(stability, 5.0)
        r2 = get_retrievability(stability, 10.0)
        r3 = get_retrievability(stability, 15.0)
        assert r1 > r2 > r3, f"保留率应单调递减：{r1} > {r2} > {r3}"


class TestGetInterval:
    """间隔计算测试"""

    def test_interval_at_dr_09(self):
        """当 DR=0.9 时，interval 应等于 round(stability)"""
        stability = 10.0
        interval = get_interval(stability, 0.9)
        assert interval == 10, f"DR=0.9 时 interval 应为 10，实际为 {interval}"

    def test_interval_at_dr_08(self):
        """当 DR=0.8 时，interval 应大于 stability"""
        stability = 10.0
        interval = get_interval(stability, 0.8)
        assert interval > 10, f"DR=0.8 时 interval 应 > 10，实际为 {interval}"

    def test_interval_at_dr_095(self):
        """当 DR=0.95 时，interval 应小于 stability"""
        stability = 10.0
        interval = get_interval(stability, 0.95)
        assert interval < 10, f"DR=0.95 时 interval 应 < 10，实际为 {interval}"

    def test_interval_dr_effectiveness(self):
        """DR 越小，间隔越长"""
        stability = 10.0
        interval_08 = get_interval(stability, 0.8)
        interval_09 = get_interval(stability, 0.9)
        interval_095 = get_interval(stability, 0.95)
        assert interval_08 > interval_09 > interval_095, \
            f"DR 越小间隔应越长：{interval_08} > {interval_09} > {interval_095}"

    def test_interval_low_stability(self):
        """当 stability < 1 时，应返回 0（进入学习状态）"""
        stability = 0.5
        interval = get_interval(stability, 0.9)
        assert interval == 0, f"stability < 1 时应返回 0，实际为 {interval}"

    def test_interval_minimum_one_day(self):
        """间隔应至少为 1 天"""
        stability = 1.0
        interval = get_interval(stability, 0.9)
        assert interval >= 1, f"间隔应至少为 1 天，实际为 {interval}"


class TestUpdateStability:
    """稳定性更新测试"""

    def test_wrong_answer_penalty(self):
        """答错后稳定性应大幅下降（降至 10%）"""
        quality = 0  # 忘了
        stability = 45.0
        difficulty = 5.0
        delta_t = 10.0
        new_stability = update_stability(quality, stability, difficulty, delta_t)
        assert new_stability < stability * 0.15, \
            f"答错后稳定性应降至 10%，实际为 {new_stability}（原 {stability}）"
        assert new_stability >= 0.5, f"稳定性最低为 0.5，实际为 {new_stability}"

    def test_correct_answer_growth(self):
        """答对后稳定性应增长"""
        quality = 3  # 简单
        stability = 10.0
        difficulty = 5.0
        delta_t = 10.0
        new_stability = update_stability(quality, stability, difficulty, delta_t)
        assert new_stability > stability, \
            f"答对后稳定性应增长，实际为 {new_stability}（原 {stability}）"

    def test_quality_2_slight_growth(self):
        """quality=2（一般）时稳定性应小幅增长"""
        quality = 2
        stability = 10.0
        difficulty = 5.0
        delta_t = 10.0
        new_stability = update_stability(quality, stability, difficulty, delta_t)
        assert new_stability > stability, \
            f"quality=2 时稳定性应增长，实际为 {new_stability}"
        # 增长幅度应小于 quality=3
        new_stability_3 = update_stability(3, stability, difficulty, delta_t)
        assert new_stability < new_stability_3, \
            f"quality=2 增长应小于 quality=3：{new_stability} < {new_stability_3}"

    def test_stability_minimum(self):
        """稳定性最低为 0.1 天"""
        quality = 0
        stability = 0.5
        difficulty = 5.0
        delta_t = 1.0
        new_stability = update_stability(quality, stability, difficulty, delta_t)
        assert new_stability >= 0.1, f"稳定性最低为 0.1，实际为 {new_stability}"


class TestUpdateDifficulty:
    """难度更新测试"""

    def test_quality_2_decreases_difficulty(self):
        """quality=2（一般）时难度应微降"""
        quality = 2
        difficulty = 5.0
        new_difficulty = update_difficulty(quality, difficulty)
        assert new_difficulty < difficulty, \
            f"quality=2 时难度应降低，实际为 {new_difficulty}（原 {difficulty}）"
        # 降幅应较小（约 0.15）
        assert new_difficulty > difficulty - 0.3, \
            f"quality=2 降幅应较小，实际为 {new_difficulty}"

    def test_quality_3_decreases_difficulty_more(self):
        """quality=3（简单）时难度应明显降低"""
        quality = 3
        difficulty = 5.0
        new_difficulty = update_difficulty(quality, difficulty)
        assert new_difficulty < difficulty - 0.15, \
            f"quality=3 时难度应明显降低，实际为 {new_difficulty}"

    def test_quality_0_increases_difficulty(self):
        """quality=0（忘了）时难度应升高"""
        quality = 0
        difficulty = 5.0
        new_difficulty = update_difficulty(quality, difficulty)
        assert new_difficulty > difficulty, \
            f"quality=0 时难度应升高，实际为 {new_difficulty}（原 {difficulty}）"

    def test_difficulty_bounds(self):
        """难度应在 1.0~10.0 范围内"""
        # 测试下限
        quality = 4
        difficulty = 1.5
        new_difficulty = update_difficulty(quality, difficulty)
        assert new_difficulty >= 1.0, f"难度下限为 1.0，实际为 {new_difficulty}"

        # 测试上限
        quality = 0
        difficulty = 9.5
        new_difficulty = update_difficulty(quality, difficulty)
        assert new_difficulty <= 10.0, f"难度上限为 10.0，实际为 {new_difficulty}"


class TestFsrsSchedule:
    """端到端调度测试"""

    def test_schedule_returns_tuple(self):
        """fsrs_schedule 应返回 4 元组"""
        quality = 3
        stability = 10.0
        difficulty = 5.0
        delta_t = 10.0
        result = fsrs_schedule(quality, stability, difficulty, delta_t)
        assert len(result) == 4, f"应返回 4 元组，实际为 {len(result)} 元组"
        new_s, new_d, interval, base_interval = result
        assert isinstance(new_s, float), f"new_stability 应为 float"
        assert isinstance(new_d, float), f"new_difficulty 应为 float"
        assert isinstance(interval, int), f"interval 应为 int"
        assert isinstance(base_interval, int), f"base_interval 应为 int"

    def test_schedule_with_good_quality(self):
        """答对时（quality=3）应增长稳定性、降低难度、增加间隔"""
        quality = 3
        stability = 10.0
        difficulty = 5.0
        delta_t = 10.0
        new_s, new_d, interval, base_interval = fsrs_schedule(
            quality, stability, difficulty, delta_t
        )
        assert new_s > stability, f"答对后稳定性应增长"
        assert new_d < difficulty, f"答对后难度应降低"
        assert interval >= 1, f"间隔应至少为 1 天"

    def test_schedule_with_bad_quality(self):
        """答错时（quality=0）应大幅降低稳定性、升高难度"""
        quality = 0
        stability = 45.0
        difficulty = 5.0
        delta_t = 10.0
        new_s, new_d, interval, base_interval = fsrs_schedule(
            quality, stability, difficulty, delta_t
        )
        assert new_s < stability * 0.15, f"答错后稳定性应大幅下降"
        assert new_d > difficulty, f"答错后难度应升高"

    def test_schedule_respects_desired_retention(self):
        """desired_retention 参数应影响间隔"""
        quality = 3
        stability = 10.0
        difficulty = 5.0
        delta_t = 10.0
        _, _, interval_09, _ = fsrs_schedule(quality, stability, difficulty, delta_t, 0.9)
        _, _, interval_08, _ = fsrs_schedule(quality, stability, difficulty, delta_t, 0.8)
        assert interval_08 > interval_09, \
            f"DR=0.8 间隔应大于 DR=0.9：{interval_08} > {interval_09}"


class TestInitMemoryState:
    """新题初始化测试"""

    def test_init_quality_2(self):
        """quality=2 时应初始化 S=3, D=5"""
        s, d = init_memory_state(2)
        assert s == 3.0, f"quality=2 时 S 应为 3.0，实际为 {s}"
        assert d == 5.0, f"quality=2 时 D 应为 5.0，实际为 {d}"

    def test_init_quality_3(self):
        """quality=3 时应初始化 S=5, D=4"""
        s, d = init_memory_state(3)
        assert s == 5.0, f"quality=3 时 S 应为 5.0，实际为 {s}"
        assert d == 4.0, f"quality=3 时 D 应为 4.0，实际为 {d}"

    def test_init_quality_4(self):
        """quality=4 时应初始化 S=8, D=3"""
        s, d = init_memory_state(4)
        assert s == 8.0, f"quality=4 时 S 应为 8.0，实际为 {s}"
        assert d == 3.0, f"quality=4 时 D 应为 3.0，实际为 {d}"


class TestPredictReviewLoad:
    """复习负载预测测试"""

    def test_predict_review_load_format(self, temp_db):
        """predict_review_load 应返回日期字符串到整数的字典"""
        db_path, conn = temp_db
        # 插入测试数据
        user_id = 1
        subject_id = 1
        question_id = "1.1-01"
        now = datetime.now()
        next_review = (now + timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO review_schedule
            (user_id, question_id, subject_id, interval, next_review)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, question_id, subject_id, 10, next_review))
        conn.commit()

        # Mock get_db 返回测试连接
        import models
        original_get_db = models.get_db
        models.get_db = lambda: conn

        try:
            load = predict_review_load(user_id, subject_id, days=30)
            assert isinstance(load, dict), f"应返回 dict，实际为 {type(load)}"
            # 检查键格式为 YYYY-MM-DD
            for key in load.keys():
                assert len(key) == 10, f"日期键应为 YYYY-MM-DD 格式：{key}"
                assert key[4] == '-' and key[7] == '-', f"日期格式错误：{key}"
            # 检查值为正整数
            for value in load.values():
                assert isinstance(value, int), f"值应为 int，实际为 {type(value)}"
                assert value > 0, f"值应为正整数，实际为 {value}"
        finally:
            models.get_db = original_get_db

    def test_predict_review_load_calculation(self, temp_db):
        """predict_review_load 应正确计算复习次数"""
        db_path, conn = temp_db
        user_id = 1
        subject_id = 1
        question_id = "1.1-01"
        now = datetime.now()

        # 先插入题目（predict_review_load 需要 JOIN questions 表）
        conn.execute("""
            INSERT INTO questions (id, stem, answer, subject_id, status)
            VALUES (?, '测试题', 'A', ?, 1)
        """, (question_id, subject_id))

        # 设置 next_review 为 5 天后，interval 为 10 天
        next_review = (now + timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO review_schedule
            (user_id, question_id, subject_id, interval, next_review, card_state)
            VALUES (?, ?, ?, ?, ?, 'review')
        """, (user_id, question_id, subject_id, 10, next_review))
        conn.commit()

        import models
        original_get_db = models.get_db
        models.get_db = lambda: conn

        try:
            load = predict_review_load(user_id, subject_id, days=30)
            # 在 30 天内，第 5 天和第 15 天、第 25 天应有复习
            # 总共约 3 次
            total_reviews = sum(load.values())
            assert total_reviews >= 2, \
                f"30 天内应至少有 2 次复习，实际为 {total_reviews}"
            assert total_reviews <= 4, \
                f"30 天内应最多有 4 次复习，实际为 {total_reviews}"
        finally:
            models.get_db = original_get_db


class TestAlgorithmIntegration:
    """算法集成测试"""

    def test_full_review_cycle(self):
        """完整复习周期：新题 → 学习 → 复习 → 掌握"""
        # 新题首次答对（quality=3）
        quality = 3
        stability = 1.0
        difficulty = 5.0
        delta_t = 1.0

        # 第 1 次复习
        new_s, new_d, interval, _ = fsrs_schedule(
            quality, stability, difficulty, delta_t
        )
        assert new_s > stability, "第 1 次复习后稳定性应增长"
        assert interval >= 1, "间隔应至少为 1 天"

        # 第 2 次复习（假设在 interval 天后）
        delta_t_2 = interval
        new_s_2, new_d_2, interval_2, _ = fsrs_schedule(
            quality, new_s, new_d, delta_t_2
        )
        assert new_s_2 > new_s, "第 2 次复习后稳定性应继续增长"

        # 第 3 次复习后答错
        delta_t_3 = interval_2
        new_s_3, new_d_3, interval_3, _ = fsrs_schedule(
            0,  # 忘了
            new_s_2, new_d_2, delta_t_3
        )
        assert new_s_3 < new_s_2 * 0.15, "答错后稳定性应大幅下降"
        assert new_d_3 > new_d_2, "答错后难度应升高"

    def test_desired_retention_affects_learning_speed(self):
        """desired_retention 应影响学习速度"""
        quality = 3
        stability = 5.0
        difficulty = 5.0
        delta_t = 5.0

        # 低 DR（0.8）：间隔更长，学习更快
        _, _, interval_08, _ = fsrs_schedule(
            quality, stability, difficulty, delta_t, 0.8
        )

        # 高 DR（0.95）：间隔更短，学习更慢
        _, _, interval_095, _ = fsrs_schedule(
            quality, stability, difficulty, delta_t, 0.95
        )

        assert interval_08 > interval_095, \
            f"低 DR 应有更长间隔：{interval_08} > {interval_095}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
