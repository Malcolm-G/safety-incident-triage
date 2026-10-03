"""The invented data must not look like a real event at a real airline or airport.

Real names are stored here only as hashes, so this repo never contains them.
Words and short word groups from every text file in the repo are hashed and compared.
"""
import hashlib
import re

import config
from triage.loader import load_reports

# sha256 of well-known real airline, airport and city names (lowercase words joined by one space).
REAL_NAME_HASHES = {
    "083a7007cae55b4262cf0019f5e7f5c2495679cb6eecdccd6859b3e2c352dccb",
    "0c42574f4b9a1745403f34328849b8c83841aab21a1e8dafa8835dd2991b5340",
    "121592d5e6cab529da69fc589e2bd1b92fbbb2f7139275dbfa612d303f9e2e56",
    "15cb41f1adc95ad4f19386c0ad1be2fd2749d781380a5096b7004860ec2fa608",
    "1670f2e42fefa5044d59a65349e47c566009488fc57d7b4376dd5787b59e3c57",
    "16b4ceef84eec6d6a927b90911c3cca3d2ce9d718be1fcd1aadd7a9cd4a268b9",
    "16f45b99abfda6364208cc5d3308269813641fab3ed9ad56affa18b1783280b7",
    "21bd3229a131a2cc251bf2dde8a900bd318d92c7aad7d33e72e54f581c306e86",
    "22ff277b10da3a6fbabf7b4a7385855f24fe3bb04a4688bbf35d092a0740344c",
    "25a89501122fbd332d8166134a164f99eaf3b96e4b9defe091a93fa8466feb84",
    "26c98ec3b46b0a4f7bd5e464268df74a0ca7af24f2f1ec6cfdc27b5122a598fa",
    "2bc44192bef3f5a3f26d2763af4bc7fd1356a658d65d0918f610689cdf7cc19c",
    "2da257a8b5d1aa748e2deb83808162754c96f6c6fcf54a5dbc5fb58d3aa06d16",
    "30f9f098c86ce1bd5b3fa3b6de8a95f1ce611903f5759e8bb1cee83128120cd1",
    "3487f039ba66aaafa3e1e6a3d9eea6befb1249e7e3428e25eeb9817120629f07",
    "36aa04f4333ebc94260a496b27815226e288d9f946e5eca92362e42c09626290",
    "40ace5b4f58193240d4006e6468fa37fdf64111407672475b0a804b4a76d0339",
    "42be7e62d696dea50d732f0929e2ac081ea2d9c2699b9eafad336547fbd2c044",
    "4757d64f0af944705f5ed95ed5b5574fed0be688fffa1e245015625ad2e5ee2e",
    "51b5cc296a2f0acb1d8095328cea70021b5c32cea7c66a57b3e464859fdd127c",
    "53d0c4e8e5a91531b91d50ee523521ad1236fed683e7643f44c80985363cacde",
    "5725fe1dbbb230d3b6a20e89a31de1cdb501b9564d410216df64db76903c1f0c",
    "5ef0f7ce422bd747f14de727237022aafc2bb5f51743f4e3c41ced278d5633cb",
    "6089854c94ca5454b76be6752c562901a985f64c9a946f62976aeab593b83161",
    "62441464c4e3b0bacc01a48a640ac9c61805bca5b8f3d50a9d8df2fbd828728e",
    "62f3cef2de450f41a029d142af609faabe187f79431cac037b9057866793406d",
    "6441d520c70fef6eb4cd88db702183fea02511d8b06e4d68fac187f82a8d47d4",
    "6b3d159fc7df79ae7af32023954f360975e9e645cdd9b507ca0a3b83ee984b63",
    "751c59fe1fa734e61bec7c142171bfcbca97ff8223171b4bd63d8165a67a4d74",
    "785d933e00a9a0c5409ccde4e2d9bac100c0f181fd9948d3d22401ff58aaa2d2",
    "803bd65441cc811070ad7391f855454b4953cbbd5c15f4757658e32bb6377ce0",
    "8417bed310833297d586cc6747ebc0d8da64a30b75946e3cced61f621f55e43a",
    "87e94f5c862d6bda17a2c4006ef90b322bba62d1f4bb4d4763bb69df2527dedd",
    "8f2c868df7896234381f95886df1a83cf64d448c98babd24cd8b45ced732e484",
    "91716d23a20ea3d2c19b4c4c6d5ca593cead3f267647fa857a381ea85cfdf365",
    "996a05e70dad69bb9bdfd5b43fdc399843686dd6b472e8fda851dcd61a41cba8",
    "9c6ba6d4b11b7409fc03ee60286cbc91da8fc62414acd55fd898dd56614c4c48",
    "9f2608067816e38c85edfb0c3985feff32def8b5dc17bb522ffc2e877e9b386b",
    "a526402cb28e47797a2d41d233b38540334b8734a92e268083a1e1878c912e5d",
    "a5c49775b0a68d9f4dbd6c5cf41ed119aaf4c3df1a2a0f6c06c2ac966ab43e04",
    "afe04579004049ccce1843a40bdf9eb85f3a4839390375e35d0018a7f9aa70c8",
    "b11e23303e7d8bc69ecf65d611409528002d7a0151abbd93de3d325908d69498",
    "b392acdcfd33f02009db6c858da8a10be0b21080fdca65fcc56dda798cb85c2a",
    "ba2436bd25a09dd572c044797e6978eaa9c498fb36fa0f59fb672ca03cc3faf7",
    "bd732730bd39834d83bf92a114960180d3bd4a6f1309307165e6f30ed9846fdd",
    "c43e7c939fa155a152360078db19817db3d6a1abb3b48ed60b8342f0b4882c59",
    "d0bc5835c717795e3711d3503dc47a13c9d1bbbd2f7874674379d2692231dbaa",
    "d209bcc17778fd19fd2bc0c99a3868bf011da5162d3a75037a605768ebc276e2",
    "d6db21ddecbbd0eeccb901c7fae837ca86cec4c289d7784e9a7016855f10859b",
    "d7dbb1f2d24ee93a5f18895745eb637b1f2258a48c80d04c01f5fa2dda122412",
    "dae16a865a6af1a8ae5f5d2f95399725f0f93236213b60adcb6d9907c4f147b4",
    "dc930d31d2ac87e5395f225548fb267662bd209b5d974cc8fac3458d7c8fc143",
    "e121f18e84b81f8408c40f80c20c3191046b3e58b81772fb18dfcb1b26249edc",
    "e65822f83a00fc74b79bd06086601d24edb07617abf1d89c14daf92c766a0994",
    "e8032604447171cc6e65cfb98ff38ccbf9f5f9113e0cb63060533ed86ad0032e",
    "eafb7890e80686840e6ae39907122f4819f89b988fba96c63b7b875ceeb00695",
    "eb109477ba29675ea5281574a7deeafa2ffbd237270ad22a79ba1fe8b886f4e5",
    "f156565db121455e6cc76d58a2d17f1ea7024d542a6d53a2697e4a830f7be00c",
    "fadef7fb883f49ccc9adc407e6ef686a1558f5c88f8bd1551ef4e2d2ec697ab0",
}

SKIP_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", ".playwright-mcp", "scratch"}
TEXT_SUFFIXES = {".csv", ".md", ".txt", ".json", ".py", ".ini", ".example", ".toml"}


def repo_text_files():
    for path in config.ROOT.rglob("*"):
        if path.is_dir() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name in {".gitignore", ".env.example"}:
            yield path


def word_groups(text: str):
    words = re.findall(r"[a-z0-9]+", text.lower())
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            yield " ".join(words[i:i + n])


def real_names_in(text: str) -> set[str]:
    return {g for g in word_groups(text) if hashlib.sha256(g.encode()).hexdigest() in REAL_NAME_HASHES}


def test_no_real_airline_airport_or_city_names_anywhere_in_the_repo():
    hits = {}
    for path in repo_text_files():
        if path.name == "test_synthetic_not_real.py":
            continue  # holds only hashes; skipping avoids hashing its own hex strings
        found = real_names_in(path.read_text(encoding="utf-8", errors="ignore"))
        if found:
            hits[str(path.relative_to(config.ROOT))] = len(found)
    assert not hits, f"real-looking names found in: {hits}"


def test_the_guard_itself_catches_a_real_name():
    assert real_names_in("the flight to heathrow was late")  # a known name must be caught
    assert not real_names_in("the Kelvara 214 aircraft at Marrowby Field")


def test_flight_identifiers_are_invented_not_airline_codes():
    # real flight numbers look like two capital letters then digits (for example AB1234)
    pattern = re.compile(r"\b[A-Z]{2}\s?\d{2,4}\b")
    for r in load_reports():
        assert not pattern.search(r.text), f"{r.report_id} has a real-looking flight code"


def test_no_email_addresses_or_email_headers_in_the_repo():
    email = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    header = re.compile(r"^\s*(From|To|Cc|Subject):", re.M)
    for path in repo_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not email.search(text), path
        if path.suffix in {".csv", ".md", ".txt"}:
            assert not header.search(text), path


def test_no_api_key_strings_in_the_repo():
    marker = "sk-" + "ant"
    for path in repo_text_files():
        assert marker not in path.read_text(encoding="utf-8", errors="ignore"), path
