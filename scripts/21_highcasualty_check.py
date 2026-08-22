import csv, datetime as dt, os, time
from pathlib import Path
from dotenv import load_dotenv
import mediacloud.api

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
search = mediacloud.api.SearchApi(os.environ["MEDIACLOUD_API_KEY"])
COLLECTION_ID = 9272347

CASES = [
    ("LD-2026-03-06-صيدا (Sidon)", dt.date(2026, 3, 6), [
        '("Sidon" OR "Saida") AND Lebanon AND ("Makassed" OR "Al-Maqassed" OR hospital)',
    ]),
    ("LD-2026-03-07-جبشيت (Jbeshit)", dt.date(2026, 3, 7), [
        '("Jbeshit" OR "Jbaachit" OR "Jbchit" OR "Jbisheet") AND Lebanon',
    ]),
    ("LD-2026-03-08-تفاحتا (Tfahta)", dt.date(2026, 3, 8), [
        '("Tfahta" OR "Tafahta" OR "Toufahta" OR "Tuffahta") AND Lebanon',
    ]),
    ("LD-2026-03-11-شعت (Chaat)", dt.date(2026, 3, 11), [
        '("Chaat" OR "Shaat" OR "Chaath" OR "Chaat village") AND Lebanon',
    ]),
    ("LD-2026-03-11-الشهابية (Al-Shihabiyeh)", dt.date(2026, 3, 11), [
        '("Shihabiyeh" OR "Chihabiyeh" OR "Al-Shihabiyeh" OR "Chehabiyeh") AND Lebanon',
    ]),
    ("LD-2026-03-07-شمسطار (Shamsatar)", dt.date(2026, 3, 7), [
        '("Shamsatar" OR "Chamsatar" OR "Shamstar" OR "Shmustar") AND Lebanon',
    ]),
    ("LD-2026-03-27-السكسكية (Al-Suksukiyeh)", dt.date(2026, 3, 27), [
        '("Suksukiyeh" OR "Siksikiyeh" OR "Al-Suksukiyeh" OR "Sekssakiyeh") AND Lebanon',
    ]),
    ("LD-2026-03-07-كوثرية الرز (Kawthariyet al-Rez)", dt.date(2026, 3, 7), [
        '("Kawthariyet al-Rez" OR "Kaouthariyet el-Rez" OR "Kawtharieh" OR "Kawthariyeh") AND Lebanon',
    ]),
    ("LD-2026-03-07-ميفدون (Meifadoun)", dt.date(2026, 3, 7), [
        '("Meifadoun" OR "Meifdoun" OR "Meifadoune" OR "Maifadoun") AND Lebanon',
    ]),
    ("LD-2026-03-14-ميفدون (Meifadoun)", dt.date(2026, 3, 14), [
        '("Meifadoun" OR "Meifdoun" OR "Meifadoune" OR "Maifadoun") AND Lebanon',
    ]),
]

with (BASE_DIR / "scripts" / "21_highcasualty_check.progress.log").open("w", encoding="utf-8") as log:
    for ldid, event_date, queries in CASES:
        end3 = event_date + dt.timedelta(days=3)
        end7 = event_date + dt.timedelta(days=7)
        for q in queries:
            for label, end in [("d3", end3), ("d7", end7)]:
                try:
                    page, _ = search.story_list(q, start_date=event_date, end_date=end, collection_ids=[COLLECTION_ID], page_size=10)
                except Exception as e:
                    log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')} [{label}] ERROR: {e}\n")
                    time.sleep(3)
                    continue
                log.write(f"{ldid.encode('ascii','backslashreplace').decode('ascii')} [{label}] n={len(page)} q={q}\n")
                for s in page[:5]:
                    log.write(f"   [{s.get('media_name','')}] {s.get('title','').encode('ascii','backslashreplace').decode('ascii')} | {s.get('publish_date','')} | {s.get('url','')}\n")
                time.sleep(1.0)
        log.write("\n")
