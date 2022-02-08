import argparse

from http_json import http_method

MIN_SKILL = 1000
MAX_SKILL = 100000
AVR_SKILL = 40000
STD_SKILL = 20000
D = MAX_SKILL - MIN_SKILL

TOKEN = ""

problem_info = {1: {"num_users": 30, "avr_match": 1},
                2: {"num_users": 900, "avr_match": 45}}

get_method = lambda url : http_method("GET", args.base_url, url, token=TOKEN)
post_method = lambda url, data : http_method("POST", args.base_url, url, data=data, token=TOKEN)
put_method = lambda url, data : http_method("PUT", args.base_url, url, data=data, token=TOKEN)

####################
#       APIS       #
####################

def api_start(problem, init_token):
    assert 1 <= problem <= 2
    resp = http_method("POST", args.base_url, "/start", data={'problem': problem}, token=init_token, init=True)
    if type(resp) is dict:
        return resp.get('auth_key', "")
    return ""

def api_score():
    return get_method("/score")

def api_waiting_line(now):
    resp = get_method("/waiting_line").get("waiting_line", [])
    return [[d['id'], now-d['from']+1] for d in resp]

def api_game_result():
    resp = get_method("/game_result").get("game_result", [])
    return [[d['win'], d['lose'], d['taken']]for d in resp]

def api_user_info():
    resp = get_method("/user_info").get("user_info", [])
    return [[d['id'], d['grade']] for d in resp]

def api_match(data):
    return put_method("/match", {"pairs": data})

def api_change_grade(skills, num_users):
    # skills에서 value 기준으로 정렬해 id만 저장
    grades = [k for k, _ in sorted(skills.items(), key=lambda item: item[1], reverse=True)]
    # {id: index}로 저장
    commands = [{'id': id, 'grade': grades.index(id)} for id in range(1, num_users+1)]
    return put_method("/change_grade", {"commands": commands})

####################
#     FUNCTION     #
####################

# 게임 시간을 통해 두 유저의 실제 실력 차이를 추정하는 함수 (random value e의 평균값은 0이므로 생략)
def get_real_skill_diff(elapsed_time):
    return (40 - elapsed_time) * D / 35


# 두 유저의 추정 실력과 실제 차이값을 통해 값의 신뢰도를 추정하는 함수
def get_reliability(win_skill, lose_skill, real_diff):
    prob_with_lose = (lose_skill + real_diff) / (2 * lose_skill + real_diff)  # 진 유저의 추정 실력을 기준으로 확률 계산
    if 2 * win_skill - real_diff > 0:  # prob_with_win이 양수일 경우
        prob_with_win = win_skill / (2 * win_skill - real_diff)  # 이긴 유저의 추정 실력을 기준으로 확률 계산
        mean_prob = (prob_with_win + prob_with_lose) / 2  # 두 확률의 평균
    else:  # prob_with_win이 음수일 경우 prob_with_lose만 사용
        mean_prob = prob_with_lose
    return mean_prob


def solve(args):
    global TOKEN
    TOKEN = api_start(args.problem, args.init_token)
    num_users = problem_info[args.problem]['num_users']

    # skills: 각 user들의 skill 추정치
    skills = {}  # user들의 skill값을 AVR_SKILL로 초기화
    for id in range(1, num_users+1):
        skills[id] = AVR_SKILL

    # now: 현재 시각
    for now in range(595):
        # 끝난 게임들의 결과 처리
        game_result = api_game_result()
        for result in game_result:
            win, lose, elapsed = result
            estimate_diff = abs(skills[win]-skills[lose])  # 현재까지의 predict
            real_diff = get_real_skill_diff(elapsed)       # 게임 시간을 통해 얻은 ground_truth
            error_diff = estimate_diff-real_diff           # error: predict - ground_truth
            prob = get_reliability(skills[win], skills[lose], real_diff)  # 추정 신뢰도
            update_value = error_diff * prob / 2           # error에 추정 신뢰도 곱해 반영값 생성 (win과 lose 각각 반영할 것이므로 2로 나눔)
            if update_value > 0:   # diff를 줄여야 하는 경우
                skills[win] = max(MIN_SKILL, skills[win]-update_value)
                skills[lose] = min(MAX_SKILL, skills[lose]+update_value)
            elif update_value < 0: # diff를 늘려야 하는 경우
                skills[win] = max(MIN_SKILL, skills[win]+update_value)
                skills[lose] = min(MAX_SKILL, skills[lose]-update_value)

        # 대기 큐 처리
        waiting_line = api_waiting_line(now)
        # skills 기준으로 대기 큐 정렬
        waiting_line = sorted(waiting_line, key=lambda w: skills[w[0]], reverse=True)

        # match list 생성
        match_list = []
        i = 0
        while i+1 < len(waiting_line):
            # 대기 시간에 따라 diff 값에 가중치 부여
            # 0~15분을 wait_weight개의 구역으로 구분해 1~wait_weight의 값으로 diff를 나눔
            diff = (skills[waiting_line[i][0]] - skills[waiting_line[i+1][0]]) / (waiting_line[i][1]//args.wait_weight+1)
            if diff <= args.match_skill:  # matching 성공
                match_list.append([waiting_line[i][0], waiting_line[i+1][0]])
                i += 2
            else:  # matching 실패
                i += 1
        api_match(match_list)

    # 한번에 skills를 grade로 갱신
    api_change_grade(skills, num_users)
    api_match([])
    return api_score()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", type=int, default=1)              # 문제 번호
    parser.add_argument("--init-token", type=str, required=True)
    parser.add_argument("--base-url", type=str, required=True)
    parser.add_argument("--match-skill", type=int, default=STD_SKILL)  # 매칭 가능한 능력의 최대 차이
    parser.add_argument("--wait-weight", type=int, default=3)          # 매칭 대기 시간에 가중치 부여
    args = parser.parse_args()

    print(solve(args))
