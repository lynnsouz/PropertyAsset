#!/usr/bin/env python3 -I
"""Writes review/data.json: what native speakers check on the translation review page (review/).

    python3 -I scripts/review-data.py      (scripts/sync.sh runs it)

For each language under review: the key terms that repeat on every screen, then the strings its
translator was unsure about, with the current text from the app's String Catalogs
(../Property Asset, or PA_APP_DIR) and from content/i18n/.
"""
import glob
import hashlib
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = pathlib.Path(os.environ.get("PA_APP_DIR", ROOT.parent / "Property Asset"))
SITE = "https://lynnsouz.github.io/PropertyAsset/"
REPO = "lynnsouz/PropertyAsset"
PLURAL_ORDER = ["zero", "one", "two", "few", "many", "other"]

TERMS = ["Properties", "Transactions", "Dashboard", "Workspace", "Tenants", "Recurring item", "Security deposit",
         "Waiting for confirmation", "Recently Deleted", "Owner", "Admin", "Editor", "Viewer"]

# Checked in every language.
COMMON = [
    ("app", "Every cent, in any currency", "Idiom. It should read naturally and not tie the app to one currency."),
    ("web", "hero_title", "The website's headline: the same idiom."),
    ("web", "legal_english_only", "Notice shown above the Privacy Policy and Terms, which are in English only."),
    ("app", "Deleted %@ of %@ on %@ (%@)", "Activity history. The placeholders are, in order: income or expense, "
                                           "the amount, the date, the property."),
]

# What each translator flagged: (where, English key, what to check).
LANGUAGES = [
    ("ar", "العربية", "Arabic", "rtl", [
        ("app", "Spaces", "A rentable part of a property. Translated as “place” to keep it apart from the workspace. Clear?"),
        ("app", "HOA & condo fees", "Owners' association fees. Is this the usual term?"),
        ("app", "%lld bd", "Short bedroom label on property cards; it should stay short."),
        ("app", "%@ ba", "Short bathroom label on property cards; it should stay short."),
        ("app", "%lld joined", "Same text for every number (“Joined: 3”). Fine for all counts?"),
        ("app", "%lld units", "Zero, one and two are written in words. Check each form."),
        ("app", "1 %@ in %@", "Exchange-rate label, e.g. “1 USD in EUR”."),
        ("app", "e.g. Harbor Lofts", "Example name in a form field, localized rather than kept in English."),
    ]),
    ("zh-Hans", "简体中文", "Chinese (Simplified)", "ltr", [
        ("app", "%@ a year on %@", "Yield, e.g. “5% a year on $300,000”. Natural?"),
        ("app", "1 %@ in %@", "Exchange-rate label, e.g. “1 USD in EUR”."),
        ("app", "Rents", "On a tenant's page: what the tenant rents."),
        ("app", "Spaces", "Rentable parts of a property (rooms, units)."),
        ("app", "Open", "Status of a maintenance request that hasn't started."),
        ("app", "In %@ · Out %@", "Money in and money out for a period."),
        ("app", "Every", "Label of the picker for how often something repeats."),
        ("app", "Messages", "Log of what was said to or by a tenant."),
        ("app", "%lld bd", "Short bedroom label."),
        ("app", "%@ ba", "Short bathroom label."),
    ]),
    ("hi", "हिन्दी", "Hindi", "ltr", [
        ("app", "Owner", "Roles use English loanwords (ओनर, एडमिन, एडिटर, व्यूअर); co-owners of a property are मालिक. "
                         "Is the difference clear?"),
        ("app", "HOA & condo fees", "Adapted to Indian usage (society and maintenance charges)."),
        ("app", "Mortgage", "Translated as “home loan”."),
        ("app", "Utilities", "Kept as “utility bill”."),
        ("app", "Vacation", "Name of a property icon: holiday home."),
        ("app", "Landmark", "Name of a property icon: a historic or notable building. Translated as “monument”."),
        ("app", "In %@ · Out %@", "Money in and money out for a period."),
        ("app", "Rents", "On a tenant's page: what the tenant rents."),
        ("app", "e.g. Harbor Lofts", "Example name in a form field, localized."),
    ]),
    ("bn", "বাংলা", "Bengali", "ltr", [
        ("app", "Reimbursement", "Fairly formal word; “খরচ ফেরত” would be plainer. Which is better?"),
        ("app", "In %@ · Out %@", "Money in and money out for a period."),
        ("app", "Yield", "Yearly return on a property's value."),
        ("app", "HOA & condo fees", "Society and condo fees."),
        ("app", "Audit History", "Translated as “change history”."),
        ("app", "Assign All To…", "Menu action: give every item to one owner or unit."),
        ("app", "%lld bd", "Short bedroom label."),
        ("app", "%@ ba", "Short bathroom label."),
    ]),
    ("id", "Bahasa Indonesia", "Indonesian", "ltr", [
        ("app", "HOA & condo fees", "Uses IPL, an Indonesia-specific term. Fine for readers elsewhere?"),
        ("app", "Mortgage", "Uses KPR, the Indonesian home-loan term."),
        ("app", "Viewer", "Read-only role. “Pelihat” (Google's wording) or “Peninjau”?"),
        ("app", "Security deposits held", "Deposit still held (dipegang), as opposed to kept by the landlord (ditahan). Clear?"),
        ("app", "Kept (counted as income)", "The part of a deposit the landlord keeps."),
        ("app", "%lld bd", "Short bedroom label (KT)."),
        ("app", "%@ ba", "Short bathroom label (KM)."),
        ("app", "Resend code in %llds", "Countdown in seconds."),
        ("app", "e.g. Harbor Lofts", "Example name in a form field, localized."),
    ]),
    ("ja", "日本語", "Japanese", "ltr", [
        ("app", "Security deposits held", "Deposit still held."),
        ("app", "Kept (counted as income)", "The part of a deposit the landlord keeps. “Kept” has no exact match."),
        ("app", "Rents", "On a tenant's page: what the tenant rents."),
        ("app", "Open", "Status of a maintenance request that hasn't started."),
        ("app", "When due", "Option: record a recurring item when it's due."),
        ("app", "Every", "Label of the picker for how often something repeats."),
        ("app", "Report in %@?", "Question: switch the report to this currency?"),
        ("app", "Apartment", "Property type."),
        ("app", "House", "Property type."),
        ("app", "%lld bd", "Short bedroom label."),
        ("app", "%@ ba", "Short bathroom label."),
    ]),
    ("ru", "Русский", "Russian", "ltr", [
        ("app", "Every %@", "Written as “Interval: …” so the inserted text (“1 неделя”) keeps its case."),
        ("app", "Every %lld months", "Abbreviated (мес.) to avoid number agreement. Acceptable?"),
        ("app", "Every", "Label of the picker for how often something repeats."),
        ("app", "%@ · %lld overdue since %@", "e.g. “Harbor Lofts · 2 overdue since 1 Jun”."),
        ("app", "%lld bd", "Short bedroom label."),
        ("app", "%@ ba", "Short bathroom label."),
        ("app", "e.g. Harbor Lofts", "Example name in a form field, localized (with quotation marks inside)."),
    ]),
]


def load_catalog() -> dict:
    strings: dict = {}
    for path in glob.glob(str(APP / "**/Localizable.xcstrings"), recursive=True):
        if "/.build/" in path or "/build/" in path:
            continue
        for key, entry in json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["strings"].items():
            strings.setdefault(key, entry)
    return strings


def app_text(catalog: dict, key: str, lang: str) -> tuple[str, bool]:
    loc = catalog.get(key, {}).get("localizations", {}).get(lang)
    assert loc, f"{lang}: no translation of {key!r}"
    if "stringUnit" in loc:
        return loc["stringUnit"]["value"], False
    forms = loc["variations"]["plural"]
    return "\n".join(f"{f}: {forms[f]['stringUnit']['value']}" for f in PLURAL_ORDER if f in forms), True


def item(group: str, where: str, english: str, current: str, note: str, plural: bool, key: str) -> dict:
    ident = hashlib.sha1(f"{where}:{key}".encode()).hexdigest()[:10]
    return {"id": ident, "group": group, "where": where, "key": key, "english": english,
            "current": current, "note": note, "plural": plural}


def main() -> None:
    catalog = load_catalog()
    english_web = json.loads((ROOT / "content/i18n/en.json").read_text(encoding="utf-8"))
    languages = []
    for code, native, name, direction, flagged in LANGUAGES:
        web = json.loads((ROOT / f"content/i18n/{code}.json").read_text(encoding="utf-8"))
        items = []
        for term in TERMS:
            current, plural = app_text(catalog, term, code)
            items.append(item("term", "App", term, current, "", plural, term))
        for where, key, note in COMMON + flagged:
            if where == "web":
                text = lambda s: s.replace("&nbsp;", " ")
                items.append(item("check", "Website", text(english_web[key]), text(web[key]), note, False, key))
            else:
                current, plural = app_text(catalog, key, code)
                items.append(item("check", "App", key, current, note, plural, key))
        languages.append({"code": code, "native": native, "name": name, "dir": direction,
                          "site": f"{SITE}{code.lower()}/", "items": items})
    out = ROOT / "review" / "data.json"
    out.write_text(json.dumps({"repo": REPO, "languages": languages}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ Review data: {sum(len(l['items']) for l in languages)} items in {len(languages)} languages")


if __name__ == "__main__":
    main()
