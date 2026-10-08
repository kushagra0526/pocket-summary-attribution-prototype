"""Write the synthetic benchmark: 6 recordings, each with a speaker-tagged transcript, a summary
containing planted mistakes, and ground-truth labels per summary line.

labels: "ok" | "mis:<RightSpeaker>" | "unsupported". All people and conversations are made up.
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "data" / "meetings"

MEETINGS = [
    {
        "id": "01-reading-group",
        "title": "Reading group (2 speakers)",
        "segments": [
            ["Mark", 5, "Okay, let's start. Last week we finished chapter three of Ephesians."],
            ["Anna", 31, "Right. I think the passage on unity is the strongest part of the letter."],
            ["Mark", 62, "I found the household codes section harder to read, honestly."],
            ["Anna", 100, "For next week I'll write the discussion questions for chapter four."],
            ["Mark", 134, "Great. I'll book the community hall for Thursday evening."],
            ["Anna", 170, "Can we also invite the youth group? They asked about joining."],
            ["Mark", 200, "Yes, I'll email the youth group leader tonight."],
        ],
        "summary": [
            "## Summary",
            ("- Anna said the passage on unity is the strongest part of the letter.", "ok"),
            ("- Mark found the household codes section harder to read.", "ok"),
            ("- Mark suggested inviting the youth group.", "mis:Anna"),
            "## Action items",
            ("- Mark: write the discussion questions for chapter four.", "mis:Anna"),
            ("- Mark: book the community hall for Thursday.", "ok"),
            ("- Anna: email the youth group leader.", "mis:Mark"),
        ],
    },
    {
        "id": "02-sales-call",
        "title": "Sales call (3 speakers, hand-off)",
        "segments": [
            ["Priya", 4, "Thanks for making time, Tom. Today I want to walk through pricing and the security review."],
            ["Tom", 40, "Our main concern is single sign-on. Our IT team requires SAML for every vendor."],
            ["Dev", 75, "We support SAML with Okta and Azure AD today, and SCIM provisioning is on the roadmap for March."],
            ["Tom", 118, "Good. Legal will also need your SOC 2 report before we can sign."],
            ["Priya", 150, "Dev, can you send Tom the SOC 2 report and the security questionnaire?"],
            ["Dev", 161, "Sure, I'll get both over by Wednesday."],
            ["Tom", 190, "On pricing, we'd need annual billing and a discount above two hundred seats."],
            ["Priya", 225, "I'll put together an annual quote for two hundred and fifty seats."],
        ],
        "summary": [
            "## Summary",
            ("- Tom said their IT team requires SAML for every vendor.", "ok"),
            ("- Priya said SCIM provisioning is on the roadmap for March.", "mis:Dev"),
            ("- Tom asked for annual billing and a discount above two hundred seats.", "ok"),
            "## Action items",
            ("- Priya: send Tom the SOC 2 report and security questionnaire by Wednesday.", "mis:Dev"),
            ("- Dev: prepare an annual quote for two hundred and fifty seats.", "mis:Priya"),
            ("- Dev: schedule a demo of SCIM for the IT team next week.", "unsupported"),
        ],
    },
    {
        "id": "03-standup",
        "title": "Engineering standup (3 speakers)",
        "segments": [
            ["Lena", 3, "Quick standup. The Android build failed again last night on the Bluetooth pairing test."],
            ["Omar", 25, "That's the flaky test. I'll quarantine it and open a ticket to fix the timeout."],
            ["Jess", 52, "Firmware 2.3 is ready for beta. I'll roll it out to the internal testers today."],
            ["Lena", 80, "Jess, could you also write the release notes for the beta?"],
            ["Jess", 88, "Yep, will do."],
            ["Omar", 105, "Heads up, the transcription queue backed up yesterday afternoon. Latency hit forty seconds."],
            ["Lena", 140, "Let's add an alert when queue latency goes above twenty seconds. I'll set that up."],
        ],
        "summary": [
            "## Summary",
            ("- Lena reported the Android build failed on the Bluetooth pairing test.", "ok"),
            ("- Omar said the transcription queue latency hit forty seconds.", "ok"),
            ("- Jess will quarantine the flaky test.", "mis:Omar"),
            "## Action items",
            ("- Jess: roll out firmware 2.3 to internal testers.", "ok"),
            ("- Omar: write the release notes for the beta.", "mis:Jess"),
            ("- Lena: add an alert when queue latency goes above twenty seconds.", "ok"),
            ("- Omar: migrate the queue to Kafka.", "unsupported"),
        ],
    },
    {
        "id": "04-phone-call",
        "title": "Phone call via contact mic (2 speakers, unnamed request)",
        "segments": [
            ["Rosa", 2, "Riverside Clinic, this is Rosa. How can I help?"],
            ["Sam", 8, "Hi, I need to move my physio appointment from Tuesday to Friday morning."],
            ["Rosa", 20, "Friday at nine thirty is open. I'll move you to that slot."],
            ["Sam", 35, "Perfect. Also my insurance changed, I have a new member card."],
            ["Rosa", 48, "Then please bring the new insurance card on Friday so we can update your file."],
            ["Sam", 62, "Will do. I'll bring it."],
        ],
        "summary": [
            "## Summary",
            ("- Sam asked to move the physio appointment from Tuesday to Friday.", "ok"),
            ("- Rosa said the insurance changed and there is a new member card.", "mis:Sam"),
            "## Action items",
            ("- Rosa: move Sam's appointment to Friday at nine thirty.", "ok"),
            ("- Rosa: bring the new insurance card on Friday.", "mis:Sam"),
        ],
    },
    {
        "id": "05-interview",
        "title": "Interview (speaker name leaked from another recording)",
        "segments": [
            ["Maya", 5, "Thanks for coming in, Chris. Tell me about a project you're proud of."],
            ["Chris", 15, "I led the migration of our payments service from a monolith to Go microservices."],
            ["Maya", 70, "How did you handle the cutover without downtime?"],
            ["Chris", 80, "We ran both systems in parallel for two weeks and compared every ledger entry nightly."],
            ["Maya", 150, "Our team is mostly Python today, with some Rust in the audio pipeline."],
            ["Chris", 185, "I'd be happy to learn Rust. I've only used it for side projects."],
            ["Maya", 220, "Great. I'll send you the take-home assignment by Monday."],
        ],
        "summary": [
            "## Summary",
            ("- John described leading the payments service migration to Go microservices.", "mis:Chris"),
            ("- Chris said both systems ran in parallel for two weeks with a nightly ledger check.", "ok"),
            ("- Maya said the team is mostly Python with some Rust in the audio pipeline.", "ok"),
            "## Action items",
            ("- Chris: send the take-home assignment by Monday.", "mis:Maya"),
        ],
    },
    {
        "id": "06-founders-sync",
        "title": "Founders sync (3 speakers, hand-off)",
        "segments": [
            ["Ravi", 4, "Retail partners want the device in stores by November. We need forty thousand units."],
            ["Mei", 40, "The factory can do thirty thousand units in October if we lock the order this week."],
            ["Carlos", 75, "Cash wise we can cover the deposit, but I want the payment terms at net sixty."],
            ["Ravi", 110, "Mei, can you negotiate net sixty with the factory?"],
            ["Mei", 118, "Yes, I'll call them tomorrow morning."],
            ["Carlos", 150, "I'll update the cash forecast with the new order size."],
            ["Mei", 180, "We should also redesign the packaging for retail shelves."],
            ["Ravi", 200, "Agreed, I'll brief the design agency on the packaging."],
        ],
        "summary": [
            "## Summary",
            ("- Ravi said retail partners want the device in stores by November.", "ok"),
            ("- Carlos said the factory can do thirty thousand units in October.", "mis:Mei"),
            ("- Mei suggested redesigning the packaging for retail shelves.", "ok"),
            "## Action items",
            ("- Ravi: negotiate net sixty with the factory.", "mis:Mei"),
            ("- Carlos: update the cash forecast with the new order size.", "ok"),
            ("- Mei: brief the design agency on the packaging.", "mis:Ravi"),
            ("- Carlos: book freight for the November shipment.", "unsupported"),
        ],
    },
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for m in MEETINGS:
        lines, labels = [], {}
        for item in m["summary"]:
            if isinstance(item, tuple):
                labels[str(len(lines))] = item[1]
                lines.append(item[0])
            else:
                lines.append(item)
        doc = {"id": m["id"], "title": m["title"],
               "segments": [{"speaker": s, "start": t, "text": x} for s, t, x in m["segments"]],
               "summary": "\n".join(lines), "labels": labels}
        (OUT / f"{m['id']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(MEETINGS)} meetings to {OUT}")


if __name__ == "__main__":
    main()
