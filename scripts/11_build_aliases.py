"""
Stage 2, step 10: transliteration aliases for every location in location_day.csv.

Methodology (documented per location in the `notes` column):
- "convention": built from standard Arabic-to-English transliteration variance
  points for Lebanese place names (ya/i/ee, waw/u/w, ta-marbuta -a/-e, al- prefix
  in/out, double consonants, qaf as q/k, kha/ha, tha/dh) plus the spelling
  already established for this place in incidents.csv.
- "verified": cross-checked against real-world usage (news archives, gazetteers)
  via web search - used for the 20-unit pilot batch and a handful of larger,
  higher-profile places where getting the common form right matters most.
- "composite": not a single named place (a road or an area between two named
  villages) - aliases are the union of the constituent places' aliases, since
  that's what an article about the location would actually name.

is_ambiguous=1 marks a location whose primary English name is also an
ordinary English word or otherwise generic enough that a bare name search
would pull in unrelated results (e.g. "Tyre" the city vs. tyre/tire the
object) - these get an attack-context term added to the query per the
pilot-design instruction.
"""
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# location (must match location_day.csv's `location` column exactly) ->
# (aliases list, is_ambiguous, method, notes)
ALIASES = {
    # --- composite road/area entries: union of constituent place aliases ---
    "Aaba-Jbeshit area": (["Aaba", "Ebba", "Jbeshit", "Jbaachit", "Jbchit"], 0, "composite", "union of Aaba + Jbeshit aliases"),
    "Adloun-Abu al-Aswad area": (["Adloun", "Adlun", "Abu al-Aswad", "Abou el-Aswad"], 0, "composite", "union of Adloun + Abu al-Aswad aliases"),
    "Ain al-Mazraab road (Tibnine)": (["Tibnine", "Tebnine", "Tibnin", "Ain al-Mazraab"], 0, "composite", "anchored on Tibnine, the named town"),
    "Al-Aamriyeh checkpoint (Qlaile-Tyre road)": (["Aamriyeh", "Al-Aamriyeh", "Qlaile", "Qlayle", "Kleileh"], 0, "composite", "Tyre alias deliberately excluded here - see ambiguity note on the standalone Tyre entry; Qlaile carries this one"),
    "Al-Awainat (between Rmeish and Debel)": (["Rmeish", "Rmaich", "Debel", "Deble", "Dibl", "Awainat"], 0, "composite", "union of Rmeish + Debel aliases"),
    "Beit Yahoun-Tibnine road": (["Beit Yahoun", "Beit Yahoune", "Tibnine", "Tebnine"], 0, "composite", "union of Beit Yahoun + Tibnine aliases"),
    "Bint Jbeil-Aytaroun road": (["Bint Jbeil", "Bint Jbail", "Aytaroun", "Aitaroun"], 0, "composite", "union of Bint Jbeil + Aytaroun aliases"),
    "Burj al-Shamali road": (["Burj al-Shamali", "Bourj el-Chemali", "Burj Shemali", "Burj al-Chamali"], 0, "composite", "single named place, road qualifier dropped"),
    "Habbouch-Arabsalim area": (["Habbouch", "Habboush", "Arabsalim", "Arab Salim"], 0, "composite", "union of Habbouch + Arabsalim aliases"),
    "Habbouch-Nabatieh highway": (["Habbouch", "Habboush", "Nabatieh", "Nabatiyeh"], 0, "composite", "union of Habbouch + Nabatieh aliases"),
    "Jbeshit-Nabatieh highway": (["Jbeshit", "Jbaachit", "Nabatieh", "Nabatiyeh"], 0, "composite", "union of Jbeshit + Nabatieh aliases"),
    "Kfartebnit (Kawthar school road)": (["Kfartebnit", "Kfar Tebnit", "Kfartibnit"], 0, "composite", "single named place, road qualifier dropped"),
    "Kfartebnit-Arnoun road": (["Kfartebnit", "Kfar Tebnit", "Arnoun", "Arnoune"], 0, "composite", "union of Kfartebnit + Arnoun aliases"),
    "Kfartebnit-Arnoun-Nabatieh roundabout": (["Kfartebnit", "Kfar Tebnit", "Arnoun", "Arnoune", "Nabatieh", "Nabatiyeh"], 0, "composite", "union of three constituent place aliases"),
    "Sharqiya/Kawthariyet al-Sayad road": (["Sharqiya", "Charkiyeh", "Kawthariyet al-Sayad", "Kaouthariyet el-Siyad"], 0, "composite", "union of Sharqiya + Kawthariyet al-Sayad aliases"),
    "Zawtar al-Sharqiya road": (["Zawtar al-Sharqiya", "Zoutar el-Charkiyeh", "Zawtar East", "Zoutar Charkiye"], 0, "composite", "single named place, road qualifier dropped"),
    "Zawtar al-Sharqiya/al-Gharbiya area": (["Zawtar al-Sharqiya", "Zoutar el-Charkiyeh", "Zawtar al-Gharbiya", "Zoutar el-Gharbiyeh", "Zawtar East", "Zawtar West"], 0, "composite", "union of Zawtar al-Sharqiya + al-Gharbiya aliases"),
    "Zebdine-Nabatieh road": (["Zebdine", "Zebdin", "Zibdine", "Nabatieh", "Nabatiyeh"], 0, "composite", "union of Zebdine + Nabatieh aliases"),

    # --- named places ---
    "أركي (Arki)": (["Arki", "Erke", "Arkeh"], 0, "convention", ""),
    "أوتوستراد زحلة الكرك (Zahle-Kark highway)": (["Zahle", "Zahleh", "Kark", "Zahle-Kark highway"], 0, "composite", "highway named for Zahle city + Kark locality"),
    "الأوزاعي (Ouzai)": (["Ouzai", "Ouzai", "Awzai", "Al-Ouzai"], 0, "convention", ""),
    "البازورية (Bazouriyeh)": (["Bazouriyeh", "Bazourieh", "Bazuriyeh"], 0, "convention", ""),
    "البزالية (Bzaaliyeh)": (["Bzaaliyeh", "Bzaalieh", "Bzalieh"], 0, "convention", ""),
    "البيسارية (Beisariyeh)": (["Beisariyeh", "Bissariyeh", "Baysariyeh"], 0, "convention", ""),
    "الجميجمة (Al-Jmeijmeh)": (["Jmeijmeh", "Jmaijmeh", "Al-Jmeijmeh"], 0, "convention", ""),
    "الجناح (Jnah)": (["Jnah", "Jnaah"], 0, "verified", "Beirut neighborhood, common form is 'Jnah'"),
    "الحازمية (Hazmieh)": (["Hazmieh", "Hazmiyeh", "Hazmiye"], 0, "verified", "well-known Beirut-suburb name"),
    "الحدث (Hadath)": (["Hadath", "Hadeth", "Al-Hadath"], 0, "verified", "well-known Beirut-suburb name"),
    "الحنية (Al-Haniyeh)": (["Haniyeh", "Haniye", "El-Haniyeh"], 0, "convention", "note: distinct from the personal name 'Haniyeh' - Lebanon+attack terms mitigate false hits"),
    "الحوش (Al-Hosh)": (["Hosh", "El-Hosh", "Al-Hosh"], 0, "convention", ""),
    "الدوير (Al-Dawir)": (["Dawir", "Douair", "Ed-Doueir", "Al-Dawir"], 0, "convention", ""),
    "الرحاب (Al-Rihab, Beirut southern suburb)": (["Rihab", "Rehab", "Al-Rihab"], 0, "convention", ""),
    "الرملة البيضاء (Ramlet al-Baida)": (["Ramlet al-Baida", "Ramlet el-Baida", "Raml el-Baida", "Ramlet Al-Bayda"], 0, "verified", "well-known Beirut beach/neighborhood name"),
    "الروشة (Raouche)": (["Raouche", "Rawshe", "Rawcheh", "Al-Rawsheh"], 0, "verified", "well-known Beirut landmark name"),
    "السعيدة (Saaideh)": (["Saaideh", "Saaida", "Al-Saaideh"], 0, "convention", "Baalbek-area village, distinct from Sidon/Saida - kept out of Saaideh aliases to avoid collision"),
    "السكسكية (Al-Suksukiyeh)": (["Suksukiyeh", "Siksikiyeh", "Al-Suksukiyeh"], 0, "convention", ""),
    "السلطانية (Al-Sultaniyeh)": (["Sultaniyeh", "Soultaniyeh", "Al-Sultaniyeh"], 0, "convention", ""),
    "الشبريحة (Shabriha junction)": (["Shabriha", "Chabriha"], 0, "convention", ""),
    "الشرحبيل (Sharhabil)": (["Sharhabil", "Charhabil"], 0, "convention", ""),
    "الشرقية (Sharqiya)": (["Sharqiya village", "Charkiyeh"], 1, "convention", "generic word ('the eastern one'); ambiguous even within Lebanon (cf. Zawtar al-Sharqiya) - add district qualifier in query"),
    "الشعيتية (Al-Shaitiyeh)": (["Shaitiyeh", "Chaytiyeh", "Al-Shaitiyeh"], 0, "convention", ""),
    "الشهابية (Al-Shihabiyeh)": (["Shihabiyeh", "Chihabiyeh", "Al-Shihabiyeh"], 0, "convention", ""),
    "الشياح (Chiyah)": (["Chiyah", "Shiyah", "Al-Shiyah", "Mar Mikhael", "Mar Mikhail"], 0, "verified", "well-known Beirut-suburb names; original report also named the adjacent Mar Mikhael area"),
    "الصرفند (Al-Sarafand)": (["Sarafand", "Sarafend", "Al-Sarafand"], 0, "convention", ""),
    "الصوانة (Al-Sawwaneh)": (["Sawwaneh", "Sawaneh", "Al-Sawwaneh"], 0, "convention", ""),
    "الضاحية الجنوبية (Beirut southern suburb/Dahiye)": (["Dahiyeh", "Dahieh", "Dahiya", "Beirut southern suburb"], 0, "verified", "widely used English-media term"),
    "الطيري (Al-Tiri)": (["Tiri", "Al-Tiri", "Et-Tiri"], 0, "convention", ""),
    "العيشية (Al-Eishiyeh)": (["Eishiyeh", "Aychiyeh", "Al-Eishiyeh"], 0, "convention", ""),
    "الغازية (Ghazieh)": (["Ghazieh", "Ghaziyeh", "Al-Ghazieh"], 0, "convention", ""),
    "الغندورية (Al-Ghandouriyeh)": (["Ghandouriyeh", "Ghandourieh", "Al-Ghandouriyeh"], 0, "convention", ""),
    "الفوار (Al-Fawwar)": (["Fawwar", "Al-Fawwar", "Fawar"], 0, "convention", ""),
    "القاسمية (Qasimiyeh)": (["Qasimiyeh", "Kasmieh", "Al-Qasimiyeh"], 0, "convention", ""),
    "القطراني (Qatrani)": (["Qatrani", "Katrani", "Al-Qatrani"], 0, "convention", ""),
    "القليعة (Qlaya)": (["Qlaya", "Klaiaa", "Kleiaa"], 0, "convention", "Marjayoun-area village, distinct from Qlaile - kept separate to avoid collision"),
    "القليلة (Qlaile)": (["Qlaile", "Klaile", "Qlayleh"], 0, "convention", "Tyre-area village, distinct from Qlaya - kept separate to avoid collision"),
    "القنطرة (Qantara)": (["Qantara", "Kantara", "Al-Qantara"], 0, "convention", ""),
    "الكفور (Kfour)": (["Kfour", "Kfor", "Al-Kfour"], 0, "convention", ""),
    "المروانية (Marwaniyeh)": (["Marwaniyeh", "Marouaniye", "Al-Marwaniyeh"], 0, "convention", ""),
    "النبطية (Nabatieh city - Al-Rahibat neighborhood)": (["Nabatieh", "Nabatiyeh", "Nabatiye", "An-Nabatiyeh"], 0, "verified", "provincial capital, well-established English spelling"),
    "النبطية (Nabatieh city - northern entrance)": (["Nabatieh", "Nabatiyeh", "Nabatiye", "An-Nabatiyeh"], 0, "verified", "provincial capital, well-established English spelling"),
    "النبطية (Nabatieh city)": (["Nabatieh", "Nabatiyeh", "Nabatiye", "An-Nabatiyeh"], 0, "verified", "provincial capital, well-established English spelling"),
    "النبطية الفوقا (Nabatieh al-Fawqa)": (["Nabatieh al-Fawqa", "Nabatiyeh el-Fawqa", "Upper Nabatieh"], 0, "convention", ""),
    "النبعة (Nabaa)": (["Nabaa", "Naba", "El-Nabaa", "Bourj Hammoud"], 0, "verified", "well-known Beirut/Metn suburb names"),
    "النبي شيت (Nabi Chit)": (["Nabi Chit", "Nabi Sheet", "Nabi Shit", "Khirbeh", "Kherbet", "Sarain", "Ali al-Nahri"], 0, "verified", "commando-raid incident; place-name normalizer collapses the original 'raid also affected...' qualifier down to this key"),
    "النبي شيت (Nabi Chit/Nabi Sheet)": (["Nabi Chit", "Nabi Sheet", "Nabi Shit"], 0, "verified", "matches the study's own worked example spelling set"),
    "النجارية (Najariyeh)": (["Najariyeh", "Nejariyeh", "Al-Najariyeh"], 0, "convention", ""),
    "النميرية (Al-Nmeiriyeh)": (["Nmeiriyeh", "Numeiriyeh", "Al-Nmeiriyeh"], 0, "convention", ""),
    "بئر حسن (Bir Hassan)": (["Bir Hassan", "Beer Hassan"], 0, "verified", "well-known Beirut-suburb name"),
    "باتوليه (Batouliyeh)": (["Batouliyeh", "Batoulieh"], 0, "convention", ""),
    "باريش (Barish)": (["Barish", "Barich"], 0, "convention", ""),
    "بافيله (Bafiliyeh)": (["Bafiliyeh", "Bafilieh"], 0, "convention", ""),
    "بر الياس (Bar Elias)": (["Bar Elias", "Baar Elias"], 0, "verified", "well-known Bekaa town name"),
    "برج الشمالي (Burj al-Shamali)": (["Burj al-Shamali", "Bourj el-Chemali", "Burj Shemali"], 0, "verified", "well-known Tyre-area refugee camp/town name"),
    "برج قلاويه (Burj Qalawiyeh)": (["Burj Qalawiyeh", "Bourj Qalaouiye", "Burj Kalaouiyeh"], 0, "convention", ""),
    "برعشيت (Bar'ashit)": (["Bar'ashit", "Baraachit", "Bir'ashit"], 0, "convention", ""),
    "بريتال (Britel)": (["Britel", "Britell", "Brital"], 0, "convention", ""),
    "بشامون (Bshamoun)": (["Bshamoun", "Bchamoun"], 0, "verified", "well-known Aley-area town name"),
    "بعلبك (Baalbek city - Ras al-Ain)": (["Baalbek", "Baalbeck", "Ba'albek", "Ras al-Ain"], 0, "verified", "UNESCO-site city, canonical spelling well established"),
    "بعلبك (Baalbek city)": (["Baalbek", "Baalbeck", "Ba'albek"], 0, "verified", "UNESCO-site city, canonical spelling well established"),
    "بنت جبيل (Bint Jbeil - Saf al-Hawa area)": (["Bint Jbeil", "Bint Jbail", "Bent Jbeil"], 0, "verified", "well-known South Lebanon city name"),
    "بنت جبيل (Bint Jbeil - hospital area)": (["Bint Jbeil", "Bint Jbail", "Bent Jbeil"], 0, "verified", "well-known South Lebanon city name"),
    "بنت جبيل (Bint Jbeil city - market)": (["Bint Jbeil", "Bint Jbail", "Bent Jbeil"], 0, "verified", "well-known South Lebanon city name"),
    "بنت جبيل (Bint Jbeil city)": (["Bint Jbeil", "Bint Jbail", "Bent Jbeil"], 0, "verified", "well-known South Lebanon city name"),
    "بنت جبيل (Bint Jbeil)": (["Bint Jbeil", "Bint Jbail", "Bent Jbeil"], 0, "verified", "well-known South Lebanon city name"),
    "بيت ليف (Beit Lif)": (["Beit Lif", "Beit Leef"], 0, "convention", ""),
    "بيروت (Beirut)": (["Beirut", "Beyrouth", "Bayrut"], 0, "verified", "capital city, canonical spelling"),
    "تبنين (Tibnine)": (["Tibnine", "Tebnine", "Tibnin"], 0, "verified", "well-known South Lebanon town name"),
    "تحويطة الغدير (Tahwitat al-Ghadir)": (["Tahwitat al-Ghadir", "Tahouitat al-Ghadir", "Tahwitet el-Ghadir"], 0, "convention", ""),
    "تفاحتا (Tfahta)": (["Tfahta", "Tafahta"], 0, "convention", ""),
    "تمنين التحتا (Tamnin al-Tahta)": (["Tamnin al-Tahta", "Temnine el-Tahta", "Tamnine"], 0, "convention", ""),
    "تول (Toul)": (["Toul", "Tul"], 0, "convention", "short/generic-looking token but not an English word; low false-hit risk"),
    "جبال البطم (Jabal al-Botm)": (["Jabal al-Botm", "Jabal el-Botom"], 0, "convention", ""),
    "جبشيت (Jbeshit - separate afternoon strike)": (["Jbeshit", "Jbaachit", "Jbchit"], 0, "convention", ""),
    "جبشيت (Jbeshit)": (["Jbeshit", "Jbaachit", "Jbchit"], 0, "convention", ""),
    "جويا (Joya)": (["Joya", "Jouaiya", "Jwaya"], 0, "convention", ""),
    "حارة صيدا (Harit Saida)": (["Harit Saida", "Haret Saida", "Hara Saida"], 0, "convention", "Sidon suburb - always paired with 'Saida'/'Sidon' term so Lebanon+context filters residual ambiguity"),
    "حاروف (Haroof)": (["Haroof", "Haruf", "Harouf"], 0, "convention", ""),
    "حبوش (Habbouch)": (["Habbouch", "Habboush"], 0, "convention", ""),
    "حداثا (Hidatha)": (["Hidatha", "Hidata"], 0, "convention", ""),
    "حلتا (Halta)": (["Halta", "Hilta"], 0, "convention", ""),
    "حناويه (Hanawiyeh)": (["Hanawiyeh", "Hanawiye"], 0, "convention", ""),
    "خربة سلم (Khirbet Selm)": (["Khirbet Selm", "Khirbet Silm", "Kherbet Selm"], 0, "convention", ""),
    "خلدة (Khaldeh highway)": (["Khaldeh", "Khalde"], 0, "verified", "well-known coastal-highway town name"),
    "خلدة (Khaldeh)": (["Khaldeh", "Khalde"], 0, "verified", "well-known coastal-highway town name"),
    "دير أنطار (Deir Antar)": (["Deir Antar", "Dayr Antar"], 0, "convention", ""),
    "دير الزهراني (Deir al-Zahrani)": (["Deir al-Zahrani", "Deir ez-Zahrani"], 0, "convention", ""),
    "دير كيفا (Deir Kifa)": (["Deir Kifa", "Dayr Kifa"], 0, "convention", ""),
    "زبدين (Zebdine)": (["Zebdine", "Zebdin", "Zibdine"], 0, "convention", ""),
    "زلايا (Zalaya)": (["Zalaya", "Zellaya"], 0, "convention", ""),
    "زوطر / كفرتبنيت": (["Zawtar al-Sharqiya", "Zoutar el-Charkiyeh", "Zawtar al-Gharbiya", "Kfartebnit", "Kfar Tebnit"], 1, "composite", "explicitly ambiguous combined area from an unresolved source report - union of both villages' aliases, flagged for careful manual review of results"),
    "زوطر الشرقية (Zawtar al-Sharqiya)": (["Zawtar al-Sharqiya", "Zoutar el-Charkiyeh", "Zawtar East", "Zoutar Charkiye"], 0, "convention", ""),
    "سحمر (Sohmor)": (["Sohmor", "Sahmor", "Sohmar"], 0, "convention", ""),
    "سلعا (Sal'a)": (["Sal'a", "Salaa", "Sala'a"], 0, "convention", ""),
    "شبعا (Shebaa - outskirts)": (["Shebaa", "Chebaa", "Shabaa"], 0, "verified", "well-known South Lebanon town name (Shebaa Farms)"),
    "شبعا (Shebaa)": (["Shebaa", "Chebaa", "Shabaa"], 0, "verified", "well-known South Lebanon town name (Shebaa Farms)"),
    "شعت (Chaat - toward Younine)": (["Chaat", "Shaat", "Chaath", "Younine", "Youniine"], 0, "convention", ""),
    "شعت (Chaat)": (["Chaat", "Shaat", "Chaath"], 0, "convention", ""),
    "شقرا (Shaqra)": (["Shaqra", "Chaqra", "Shakra"], 0, "convention", ""),
    "شمسطار (Shamsatar)": (["Shamsatar", "Chamsatar", "Shamstar"], 0, "convention", ""),
    "شوكين (Shawkin)": (["Shawkin", "Chaoukine"], 0, "convention", ""),
    "صديقين (Saddiqine/Siddiqine)": (["Saddiqine", "Siddikine", "Sedikine"], 0, "convention", "district uncertain per incidents.csv, spelling kept broad"),
    "صريفا (Srifa)": (["Srifa", "Sreifa", "Sarifa"], 0, "verified", "matches the study's own worked example spelling set exactly"),
    "صور (Tyre)": (["Sour", "Tyre", "Al-Athar"], 1, "verified", "'Tyre' collides heavily with the English word for a wheel's tyre/tire - 'Sour' (the Arabic-derived spelling used in most Lebanese English-language press) is the primary alias; add attack-context terms when using 'Tyre'"),
    "صيدا (Sidon Corniche)": (["Sidon", "Saida"], 0, "verified", "well-known South Lebanon city name"),
    "صيدا (Sidon coastal road)": (["Sidon", "Saida"], 0, "verified", "well-known South Lebanon city name"),
    "صيدا (Sidon)": (["Sidon", "Saida"], 0, "verified", "well-known South Lebanon city name"),
    "صير الغربية (Sir al-Gharbiyeh)": (["Sir al-Gharbiyeh", "Seer al-Gharbiye", "Sir el-Gharbiyeh"], 0, "convention", ""),
    "طريق الشعيتية (Al-Shaitiyeh road)": (["Shaitiyeh", "Chaytiyeh"], 0, "convention", "road qualifier dropped, same as standalone Al-Shaitiyeh"),
    "طريق المطار (Airport Road)": (["Airport Road", "Beirut Airport Road", "Beirut international airport road"], 1, "convention", "generic descriptive term, not a proper noun - requires attack-context terms to avoid unrelated 'airport road' hits worldwide"),
    "طريق النبطية الفوقا (Nabatieh al-Fawqa road)": (["Nabatieh al-Fawqa", "Nabatiyeh el-Fawqa"], 0, "convention", "road qualifier dropped, same as standalone Nabatieh al-Fawqa"),
    "طريق جزين (Jezzine road)": (["Jezzine", "Jazzine", "Jezzin"], 0, "verified", "well-known South Lebanon town name"),
    "طير دبا (Tair Debba)": (["Tair Debba", "Tayr Debba", "Teir Debba"], 0, "convention", ""),
    "عبا (Aaba)": (["Aaba", "Ebba", "Aabba"], 0, "convention", ""),
    "عدلون (Adloun - outskirts)": (["Adloun", "Adlun", "Adloune"], 0, "convention", ""),
    "عدلون (Adloun)": (["Adloun", "Adlun", "Adloune"], 0, "convention", ""),
    "عرمون (Aramoun)": (["Aramoun", "Aarammoune"], 0, "verified", "well-known Aley-area town name"),
    "عرمون / السعديات": (["Aramoun", "Aarammoune", "Saadiyat", "Saadiyate"], 0, "composite", "union of Aramoun + Saadiyat aliases"),
    "علما الشعب (Alma al-Shaab)": (["Alma al-Shaab", "Alma ech-Chaab", "Alma al-Chaab"], 0, "convention", ""),
    "عيتيت (Aitit)": (["Aitit", "Aytit", "Ayteet"], 0, "convention", ""),
    "عين ابل (Ain Ebel)": (["Ain Ebel", "Ain Ebl", "Ain Aabel"], 0, "convention", ""),
    "عين الحلوة (Ain al-Hilweh camp)": (["Ain al-Hilweh", "Ein el-Hilweh", "Ain al-Helweh"], 0, "verified", "well-known Sidon refugee-camp name"),
    "قانا (Qana)": (["Qana", "Cana", "Kana"], 0, "verified", "internationally known place name from 1996/2006 strikes; 'Qana' is the standard English-press spelling"),
    "قبريحا (Qabrikha)": (["Qabrikha", "Kabrikha"], 0, "convention", ""),
    "قعقعية الجسر (Qaaqaait al-Jisr)": (["Qaaqaait al-Jisr", "Kaakaait el-Jisr", "Qaaqaaiyet al-Jisr"], 0, "convention", ""),
    "قلاويه (Qalawiyeh)": (["Qalawiyeh", "Qalaouiye", "Kalawiye"], 0, "convention", ""),
    "قلويه (Qalawiyeh)": (["Qalawiyeh", "Qalaouiye", "Kalawiye"], 0, "convention", "same place as 'قلاويه' - spelling variant already reconciled at incident-merge stage"),
    "قناريت (Qanaryet)": (["Qanaryet", "Kanariyet"], 0, "convention", ""),
    "كفرا (Kfarra)": (["Kfarra", "Kfar Raa"], 0, "convention", ""),
    "كفرتبنيت (Kfartebnit)": (["Kfartebnit", "Kfar Tebnit", "Kfartibnit"], 0, "convention", ""),
    "كفرجوز (Kfarjouz)": (["Kfarjouz", "Kfar Jouz", "Kafr Jouz"], 0, "convention", ""),
    "كفررمان (Kfarremen)": (["Kfarremen", "Kfar Remen", "Kfar Rumman", "Kfar Roummane"], 0, "verified", "matches the study's own worked example spelling set exactly"),
    "كفرصير (Kfarsir)": (["Kfarsir", "Kfar Sir"], 0, "convention", ""),
    "كوثرية الرز (Kawthariyet al-Rez - separate responder-team strike)": (["Kawthariyet al-Rez", "Kaouthariyet el-Rez", "Kawtharieh"], 0, "convention", ""),
    "كوثرية الرز (Kawthariyet al-Rez)": (["Kawthariyet al-Rez", "Kaouthariyet el-Rez", "Kawtharieh"], 0, "convention", ""),
    "كونين (Kounine)": (["Kounine", "Kawnin", "Kaounine"], 0, "convention", ""),
    "لبايا (Libaya)": (["Libaya", "Lebaya"], 0, "convention", ""),
    "مجدل سلم (Majdal Selem)": (["Majdal Selem", "Majdal Silm", "Majdel Selm"], 0, "convention", ""),
    "محرونة (Mahrouneh)": (["Mahrouneh", "Mahrouna"], 0, "convention", ""),
    "مخيم البداوي (Beddawi camp)": (["Beddawi", "Baddawi"], 0, "verified", "well-known Tripoli-area refugee-camp name"),
    "مخيم المية ومية (Mieh Mieh camp)": (["Mieh Mieh", "Miyeh Miyeh", "Miye Miye"], 0, "verified", "well-known Sidon-area refugee-camp name"),
    "مشغرة (Mashghara)": (["Mashghara", "Machghara"], 0, "convention", ""),
    "معركة (Maaraka junction)": (["Maaraka", "Maarakeh", "Maarake"], 0, "convention", ""),
    "معركة (Maaraka)": (["Maaraka", "Maarakeh", "Maarake"], 0, "convention", ""),
    "معركة البص (Maaraka al-Bass junction)": (["Maaraka al-Bass", "El Buss", "Al-Bass camp", "Maaraka"], 0, "convention", "near Tyre's well-known El-Buss/Al-Bass refugee camp"),
    "ميفدون (Meifadoun)": (["Meifadoun", "Meifdoun", "Meifadoune"], 0, "convention", ""),
    "ياطر (Yatar)": (["Yatar", "Yater"], 0, "convention", ""),
    "يحمر الشقيف (Yohmor al-Shaqif)": (["Yohmor al-Shaqif", "Yuhmur al-Shaqif", "Yohmor"], 0, "convention", ""),
}


def main():
    with (PROCESSED_DIR / "location_day.csv").open(encoding="utf-8-sig") as f:
        locations = sorted(set(r["location"] for r in csv.DictReader(f)))

    missing = [loc for loc in locations if loc not in ALIASES]
    if missing:
        with (PROCESSED_DIR / "_missing_aliases.txt").open("w", encoding="utf-8") as f:
            f.write(f"{len(missing)} locations have no alias entry:\n")
            for m in missing:
                f.write(m + "\n")
        print(f"WARNING: {len(missing)} locations missing - see _missing_aliases.txt")

    rows = []
    for loc in locations:
        aliases, is_ambiguous, method, notes = ALIASES.get(loc, ([], 0, "MISSING", "not yet built"))
        rows.append({
            "location": loc,
            "aliases": ";".join(aliases),
            "alias_count": len(aliases),
            "is_ambiguous_common_word": is_ambiguous,
            "verification_method": method,
            "notes": notes,
        })

    out_path = PROCESSED_DIR / "location_aliases.csv"
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out_path} ({len(rows)} locations)")
    print(f"verified: {sum(1 for r in rows if r['verification_method']=='verified')}, "
          f"convention: {sum(1 for r in rows if r['verification_method']=='convention')}, "
          f"composite: {sum(1 for r in rows if r['verification_method']=='composite')}")
    print(f"ambiguous (needs attack-context terms): {sum(1 for r in rows if r['is_ambiguous_common_word']==1)}")


if __name__ == "__main__":
    main()
