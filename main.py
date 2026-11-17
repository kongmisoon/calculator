"""Mini NPU Simulator

MAC(Multiply-Accumulate) 연산으로 십자가(Cross)/X 패턴을 판별하는 콘솔 앱.
- 모드 1: 3x3 필터 2개(A, B)와 패턴을 직접 입력
- 모드 2: data.json 의 필터/패턴을 일괄 판정하고 PASS/FAIL 집계
- 성능 분석: 크기별 MAC 연산 시간(10회 평균)과 연산 횟수(N^2)
- 보너스: 1차원 배열 최적화 비교, 패턴 생성기

표준 라이브러리(json, os, re, sys, time)만 사용한다.
"""

import json
import os
import re
import sys
import time

EPSILON = 1e-9          # 동점 판단 허용오차
REPEAT = 10             # 성능 측정 반복 횟수
LINE = "#" + "-" * 39

LABEL_CROSS = "Cross"
LABEL_X = "X"
UNDECIDED = "UNDECIDED"


# ---------------------------------------------------------------------------
# 데이터 구조
# ---------------------------------------------------------------------------
class Matrix:
    """n x n 2차원 배열. 값 저장(set)/조회(get)을 지원한다."""

    def __init__(self, n, fill=0.0):
        self.n = n
        self.data = [[fill] * n for _ in range(n)]

    def get(self, r, c):
        return self.data[r][c]

    def set(self, r, c, value):
        self.data[r][c] = value

    @classmethod
    def from_rows(cls, rows):
        """검증된 n x n 숫자 리스트로부터 Matrix 생성."""
        m = cls(len(rows))
        for r in range(m.n):
            for c in range(m.n):
                m.data[r][c] = float(rows[r][c])
        return m

    def flatten(self):
        """보너스: 2차원 -> 길이 N^2 의 1차원 리스트."""
        flat = [0.0] * (self.n * self.n)
        for r in range(self.n):
            base = r * self.n
            for c in range(self.n):
                flat[base + c] = self.data[r][c]
        return flat


# ---------------------------------------------------------------------------
# MAC 연산 (외부 라이브러리 없이 반복문으로 구현)
# ---------------------------------------------------------------------------
def mac(pattern, flt):
    """위치별 곱셈 후 모두 누적합. 점수(float) 반환."""
    n = pattern.n
    total = 0.0
    for r in range(n):
        prow = pattern.data[r]
        frow = flt.data[r]
        for c in range(n):
            total += prow[c] * frow[c]
    return total


def mac_flat(pattern_flat, filter_flat):
    """보너스: 1차원 배열 버전 MAC (단일 반복문)."""
    total = 0.0
    for i in range(len(pattern_flat)):
        total += pattern_flat[i] * filter_flat[i]
    return total


def measure_ms(func, repeat=REPEAT):
    """func() 를 repeat 회 호출해 1회당 평균 시간(ms)을 반환. I/O 는 포함하지 않는다."""
    elapsed = 0.0
    for _ in range(repeat):
        start = time.perf_counter()
        func()
        elapsed += time.perf_counter() - start
    return elapsed / repeat * 1000.0


# ---------------------------------------------------------------------------
# 점수 비교 / 라벨 정규화
# ---------------------------------------------------------------------------
def judge(score_cross, score_x):
    """epsilon 기반 비교. Cross / X / UNDECIDED 반환."""
    if abs(score_cross - score_x) < EPSILON:
        return UNDECIDED
    return LABEL_CROSS if score_cross > score_x else LABEL_X


def normalize_label(raw):
    """'+', 'cross' -> Cross / 'x' -> X. 알 수 없으면 None."""
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower()
    if key in ("+", "cross"):
        return LABEL_CROSS
    if key == "x":
        return LABEL_X
    return None


# ---------------------------------------------------------------------------
# 보너스: 패턴 생성기
# ---------------------------------------------------------------------------
def make_cross(n):
    m = Matrix(n)
    mid = n // 2
    for i in range(n):
        m.set(mid, i, 1.0)
        m.set(i, mid, 1.0)
    return m


def make_x(n):
    m = Matrix(n)
    for i in range(n):
        m.set(i, i, 1.0)
        m.set(i, n - 1 - i, 1.0)
    return m


# ---------------------------------------------------------------------------
# 모드 1: 사용자 입력 (3x3)
# ---------------------------------------------------------------------------
def read_matrix(title, n=3):
    """n줄을 공백 구분으로 입력받는다. 형식 오류 시 안내 후 처음부터 재입력."""
    while True:
        print("%s (%d줄 입력, 공백 구분)" % (title, n))
        rows = []
        error = None
        for _ in range(n):
            line = input()
            parts = line.split()
            if len(parts) != n:
                error = "입력 형식 오류: 각 줄에 %d개의 숫자를 공백으로 구분해 입력하세요." % n
                # 남은 줄도 소비하지 않고 바로 재입력으로 넘어간다
                break
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                error = "입력 형식 오류: 숫자가 아닌 값이 있습니다. 숫자만 입력하세요."
                break
        if error is None and len(rows) == n:
            return Matrix.from_rows(rows)
        print(error)
        print("→ %s 를 처음부터 다시 입력해 주세요.\n" % title)


def print_perf_table(rows):
    print("크기       평균 시간(ms)    연산 횟수")
    print("-" * 37)
    for n, ms, ops in rows:
        print("%-10s %-16.4f %d" % ("%dx%d" % (n, n), ms, ops))


def run_mode1():
    print("\n" + LINE + "\n# [1] 필터 입력\n" + LINE)
    filter_a = read_matrix("필터 A")
    print()
    filter_b = read_matrix("필터 B")
    print("\n✓ 필터 A, B 저장 완료")

    print("\n" + LINE + "\n# [2] 패턴 입력\n" + LINE)
    pattern = read_matrix("패턴")

    score_a = mac(pattern, filter_a)
    score_b = mac(pattern, filter_b)
    avg_ms = measure_ms(lambda: (mac(pattern, filter_a), mac(pattern, filter_b)))

    print("\n" + LINE + "\n# [3] MAC 결과\n" + LINE)
    print("A 점수: %r" % score_a)
    print("B 점수: %r" % score_b)
    print("연산 시간(평균/%d회, 필터 2개): %.4f ms" % (REPEAT, avg_ms))
    if abs(score_a - score_b) < EPSILON:
        print("판정: 판정 불가 (|A-B| < %g)" % EPSILON)
    else:
        print("판정: %s" % ("A" if score_a > score_b else "B"))

    print("\n" + LINE + "\n# [4] 성능 분석 (3x3)\n" + LINE)
    print_perf_table([(3, avg_ms / 2.0, 9)])  # 필터 1개당 평균


# ---------------------------------------------------------------------------
# 모드 2: data.json 분석
# ---------------------------------------------------------------------------
def find_data_file():
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.getcwd()):
        path = os.path.join(base, "data.json")
        if os.path.isfile(path):
            return path
    return None


def validate_square(rows, expected_n=None):
    """rows 가 숫자로 된 정사각 2차원 배열인지 검증. 문제 없으면 None, 있으면 사유 문자열."""
    if not isinstance(rows, list) or len(rows) == 0:
        return "2차원 배열이 아님"
    n = len(rows)
    for i, row in enumerate(rows):
        if not isinstance(row, list):
            return "%d번째 행이 배열이 아님" % (i + 1)
        if len(row) != n:
            return "정사각 배열이 아님 (행 %d: 열 %d개, 행 수 %d)" % (i + 1, len(row), n)
        for v in row:
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return "숫자가 아닌 값 포함 (행 %d)" % (i + 1)
    if expected_n is not None and n != expected_n:
        return "크기 불일치 (기대 %dx%d, 실제 %dx%d)" % (expected_n, expected_n, n, n)
    return None


def load_filters(raw_filters):
    """filters -> {N: {'Cross': Matrix, 'X': Matrix}}, 오류 {N: 사유}"""
    filters, errors = {}, {}
    if not isinstance(raw_filters, dict):
        return filters, errors
    for key, group in raw_filters.items():
        m = re.fullmatch(r"size_(\d+)", str(key))
        if not m:
            errors[key] = "필터 키 형식 오류 (size_N 형태 아님)"
            print("✗ %s 필터 로드 실패: %s" % (key, errors[key]))
            continue
        n = int(m.group(1))
        if not isinstance(group, dict):
            errors[n] = "필터 그룹이 객체가 아님"
            print("✗ %s 필터 로드 실패: %s" % (key, errors[n]))
            continue
        loaded, problem = {}, None
        for raw_label, rows in group.items():
            label = normalize_label(raw_label)
            if label is None:
                problem = "알 수 없는 필터 라벨 '%s'" % raw_label
                break
            bad = validate_square(rows, n)
            if bad:
                problem = "%s 필터: %s" % (label, bad)
                break
            loaded[label] = Matrix.from_rows(rows)
        if problem is None and (LABEL_CROSS not in loaded or LABEL_X not in loaded):
            problem = "Cross/X 필터 중 일부 누락"
        if problem:
            errors[n] = problem
            print("✗ %s 필터 로드 실패: %s" % (key, problem))
        else:
            filters[n] = loaded
            print("✓ %-7s 필터 로드 완료 (Cross, X)" % key)
    return filters, errors


def analyze_case(key, case, filters, filter_errors):
    """패턴 1건 분석. (status, reason) 반환. 예외 없이 FAIL 처리한다."""
    print("--- %s ---" % key)
    m = re.fullmatch(r"size_(\d+)_(\d+)", str(key))
    if not m:
        reason = "패턴 키 형식 오류 (size_N_idx 아님)"
        print("판정: 불가 | FAIL (%s)" % reason)
        return False, reason
    n = int(m.group(1))

    if not isinstance(case, dict) or "input" not in case or "expected" not in case:
        reason = "스키마 오류 (input/expected 누락)"
        print("판정: 불가 | FAIL (%s)" % reason)
        return False, reason

    expected = normalize_label(case["expected"])
    if expected is None:
        reason = "알 수 없는 expected 라벨 '%s'" % (case["expected"],)
        print("판정: 불가 | FAIL (%s)" % reason)
        return False, reason

    if n in filter_errors:
        reason = "필터 오류: %s" % filter_errors[n]
        print("판정: 불가 | FAIL (%s)" % reason)
        return False, reason
    if n not in filters:
        reason = "size_%d 필터 없음" % n
        print("판정: 불가 | FAIL (%s)" % reason)
        return False, reason

    bad = validate_square(case["input"], n)
    if bad:
        reason = "패턴 오류: %s" % bad
        print("판정: 불가 | FAIL (%s)" % reason)
        return False, reason

    pattern = Matrix.from_rows(case["input"])
    s_cross = mac(pattern, filters[n][LABEL_CROSS])
    s_x = mac(pattern, filters[n][LABEL_X])
    result = judge(s_cross, s_x)

    print("Cross 점수: %r" % s_cross)
    print("X 점수: %r" % s_x)
    if result == expected:
        print("판정: %s | expected: %s | PASS" % (result, expected))
        return True, ""
    if result == UNDECIDED:
        reason = "동점(UNDECIDED) 처리 규칙에 따라 FAIL (|Cross-X|=%.3g < %g)" % (abs(s_cross - s_x), EPSILON)
        print("판정: %s | expected: %s | FAIL (동점 규칙)" % (result, expected))
    else:
        reason = "판정 %s != expected %s" % (result, expected)
        print("판정: %s | expected: %s | FAIL" % (result, expected))
    return False, reason


def performance_table(sizes=(3, 5, 13, 25)):
    """생성한 Cross 패턴/필터로 크기별 MAC 시간을 측정."""
    rows = []
    for n in sizes:
        pattern, flt = make_cross(n), make_x(n)
        ms = measure_ms(lambda: mac(pattern, flt))
        rows.append((n, ms, n * n))
    return rows


def bonus_compare(sizes=(3, 5, 13, 25), repeat=1000):
    """보너스: 2D vs 1D MAC 비교 (동일 입력, 동일 반복 횟수)."""
    print("크기       2D(ms)      1D(ms)      개선율")
    print("-" * 44)
    for n in sizes:
        pattern, flt = make_cross(n), make_x(n)
        pf, ff = pattern.flatten(), flt.flatten()
        t2 = measure_ms(lambda: mac(pattern, flt), repeat)
        t1 = measure_ms(lambda: mac_flat(pf, ff), repeat)
        gain = (t2 - t1) / t2 * 100.0 if t2 > 0 else 0.0
        print("%-10s %-11.5f %-11.5f %.1f%%" % ("%dx%d" % (n, n), t2, t1, gain))


def run_mode2():
    path = find_data_file()
    if path is None:
        print("data.json 파일을 찾을 수 없습니다. main.py 와 같은 폴더에 두세요.")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print("data.json 읽기 실패: %s" % e)
        return
    if not isinstance(data, dict):
        print("data.json 최상위가 객체가 아닙니다.")
        return

    print("\n" + LINE + "\n# [1] 필터 로드\n" + LINE)
    filters, filter_errors = load_filters(data.get("filters"))

    print("\n" + LINE + "\n# [2] 패턴 분석 (라벨 정규화 적용)\n" + LINE)
    patterns = data.get("patterns")
    if not isinstance(patterns, dict):
        patterns = {}
        print("patterns 항목이 없거나 형식이 잘못되었습니다.")

    total, passed, failures = 0, 0, []
    for key, case in patterns.items():
        total += 1
        try:
            ok, reason = analyze_case(key, case, filters, filter_errors)
        except Exception as e:  # 어떤 경우에도 프로그램이 중단되지 않도록 케이스 단위로 격리
            ok, reason = False, "예기치 못한 오류: %s" % e
            print("판정: 불가 | FAIL (%s)" % reason)
        if ok:
            passed += 1
        else:
            failures.append((key, reason))

    print("\n" + LINE + "\n# [3] 성능 분석 (평균/%d회)\n" % REPEAT + LINE)
    print_perf_table(performance_table())
    print("\n[보너스] 2차원 vs 1차원 배열 MAC 비교 (각 1000회 평균)")
    bonus_compare()

    print("\n" + LINE + "\n# [4] 결과 요약\n" + LINE)
    print("총 테스트: %d개" % total)
    print("통과: %d개" % passed)
    print("실패: %d개" % len(failures))
    if failures:
        print("\n실패 케이스:")
        for key, reason in failures:
            print("- %s: %s" % (key, reason))
    print('\n(상세 원인 분석 및 복잡도 설명은 README.md 의 "결과 리포트" 섹션 참고)')


# ---------------------------------------------------------------------------
def main():
    print("=== Mini NPU Simulator ===\n")
    print("[모드 선택]\n")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")
    while True:
        choice = input("선택: ").strip()
        if choice in ("1", "2"):
            break
        print("1 또는 2 를 입력하세요.")
    if choice == "1":
        run_mode1()
    else:
        run_mode2()


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\n입력이 종료되어 프로그램을 마칩니다.")
        sys.exit(0)
