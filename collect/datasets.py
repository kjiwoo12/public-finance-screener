"""여섯 개 API 의 주소와 성질을 한곳에 적어 둔다.

주소를 코드 곳곳에 흩어 놓지 않는 이유는, 이 값들이 추측으로 알아낸 것이
아니라 포털 화면에서 확인한 사실이기 때문이다. 사실은 한군데 모아 두고
출처를 적어 둬야 나중에 고칠 때 무엇을 다시 확인해야 하는지 알 수 있다.

두 가지 함정이 있어 주석으로 남긴다.

1. 서비스 버전과 오퍼레이션 버전이 다르다. openApiFinaDebt3 아래는
   openXmlFinaDebt3 이 아니라 openXmlFinaDebt2 다. 규칙이 없으므로
   추측하지 말고 이 표를 고쳐야 한다.
2. 필수 파라미터 이름은 ac_year 다. 서버는 빠졌을 때 acYear 라고 알려
   주지만 그 이름으로 보내면 계속 같은 오류가 난다.
"""

from typing import NamedTuple


class Dataset(NamedTuple):
    key: str
    title: str
    path: str
    by_year: bool  # 연도별로 받아야 하는가. 코드표는 연도와 무관하다.


BASE = "https://apis.data.go.kr/B551982"

DATASETS: dict[str, Dataset] = {
    d.key: d
    for d in [
        Dataset("budget", "예산결산", "openApiBudgetFund2/openXmlBudgetFund2", True),
        Dataset("debt_scale", "부채규모", "openApiDebtScale3/openXmlDebtScale2", True),
        Dataset("fina_debt", "금융부채", "openApiFinaDebt3/openXmlFinaDebt2", True),
        Dataset("wage", "직원평균임금총괄", "openApiFullTimeTotal2/openXmlFullTimeTotal2", True),
        Dataset("mng_idx", "주요경영분석지표", "openApiMajorMngIdx2/openXmlMajorMngIdx2", True),
        Dataset("sido", "시도코드", "openApiSidoCd3/openXmlSidoCd2", False),
    ]
}

# 기관을 잇는 열쇠. 코드가 아니라 기관명 문자열이라는 점이 중요하다.
# 같은 기관이 내주는 데이터라 표기가 일관될 것으로 기대하지만, 기대일 뿐이라
# 수집 후 이름이 데이터셋마다 어긋나지 않는지 따로 확인한다.
JOIN_KEYS = ("AC_YEAR", "ENT_NAME")

# 이 저장소가 다루는 기간. 이상징후는 "작년 대비"로 잡으므로 한 해만 받으면
# 아무것도 못 본다. 다섯 해를 받아야 추세와 일회성 급증을 구별할 수 있다.
YEARS = (2020, 2021, 2022, 2023, 2024)
