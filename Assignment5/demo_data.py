"""
demo_data.py
============
Pre-scripted, offline-safe story scenes for Demo Mode.

WHY THIS EXISTS:
Live API calls (Gemini, Pollinations, TTS) can fail during demos — bad Wi-Fi,
rate limits, expired keys, etc. Demo Mode replaces every live call with data
from this file so a screen recording NEVER fails due to live API issues.

HOW IT WORKS:
Each genre has a list of scene dicts that match the Gemini JSON schema exactly.
When Demo Mode is ON, gemini_client.get_scene() returns the next dict from
this list instead of making a real API call. Scene index advances linearly
regardless of which choice button the user clicks — this gives a smooth,
predictable demo without needing a full choice-tree.

SCHEMA (mirrors Gemini JSON contract):
  story_text   : str   — 3-5 sentence narrative
  options      : list  — 2-4 choice strings
  image_prompt : str   — vivid description for image generation
  mood         : str   — tense | joyful | mysterious | neutral | triumphant
  speaker      : str   — narrator | character | villain
  commentary   : str   — director's note on plot choice
  trust_delta  : int   — how much this scene shifts trust (-10 to +10)
  is_ending    : bool  — True signals story conclusion
  ending_id    : int|None — 1-5 if is_ending else None
"""

# ─────────────────────────────────────────────────────────────────────────────
# HORROR — "The Ashwood Sanatorium"
# ─────────────────────────────────────────────────────────────────────────────
HORROR_SCENES = [
    {
        "story_text": (
            "You awaken to the smell of antiseptic and decay. "
            "The walls of Ashwood Sanatorium loom around you, paint peeling like dead skin. "
            "A rusty door at the end of the hall groans open by itself. "
            "Your phone is dead. Your last memory is a road trip that went terribly wrong. "
            "Something skitters in the darkness above the drop ceiling."
        ),
        "options": [
            "Creep toward the open door",
            "Search for a weapon first",
            "Call out to see if anyone else is here",
        ],
        "image_prompt": (
            "Abandoned mental hospital corridor at night, flickering fluorescent lights, "
            "peeling paint, long shadows, horror atmosphere, cinematic lighting"
        ),
        "mood": "tense",
        "speaker": "narrator",
        "commentary": (
            "Opening in medias res — no memory, hostile environment — "
            "immediately forces the player into survival mode."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Through the door you find a nurse's station, eerily preserved. "
            "Patient files are spread across the desk — one with your name on it. "
            "A child's voice whispers from behind a locked cabinet: 'They're watching.' "
            "The security camera above you slowly rotates, though the power should be off. "
            "A key ring hangs just inside the locked cabinet's glass panel."
        ),
        "options": [
            "Break the glass and grab the key ring",
            "Read your patient file",
            "Follow the sound of the child's voice",
        ],
        "image_prompt": (
            "Abandoned hospital nurse station, patient files scattered, "
            "broken security monitor, single candle, dark horror, cinematic"
        ),
        "mood": "mysterious",
        "speaker": "narrator",
        "commentary": (
            "The patient file twist raises the stakes — you're not just trapped, "
            "you may have always been part of this place."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "The file reveals you checked yourself in voluntarily three years ago — "
            "a fact you have zero memory of. "
            "A gaunt figure appears at the far window, backlit by lightning. "
            "It raises a hand — not threatening, but beckoning. "
            "Your pulse hammers. Every instinct screams run, but something deeper says trust it. "
            "The corridor behind you fills with the sound of shuffling feet."
        ),
        "options": [
            "Trust the figure and approach the window",
            "Run deeper into the sanatorium",
            "Barricade the door and wait for dawn",
        ],
        "image_prompt": (
            "Silhouette of a figure at a hospital window, lightning storm outside, "
            "horror, dramatic contrast, rain streaked glass, cinematic"
        ),
        "mood": "tense",
        "speaker": "narrator",
        "commentary": (
            "Classic horror dilemma: danger in front, danger behind. "
            "The trust mechanic makes the 'wrong' choice feel right."
        ),
        "trust_delta": 5,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "You approach the window. The figure is a woman — Dr. Mira Ashwood, "
            "the sanatorium's last director, who vanished in 1987. "
            "She cannot enter the building; something binds her outside. "
            "'You're the key,' she whispers through the glass. "
            "'The ritual that sealed this place — only the one who started it can undo it.' "
            "A distant scream echoes from the basement."
        ),
        "options": [
            "Ask Dr. Ashwood how to stop the ritual",
            "Demand to know why you can't remember",
            "Head to the basement immediately",
        ],
        "image_prompt": (
            "Woman's ghost at rain-soaked hospital window, pale face, Victorian clothes, "
            "lightning illuminating her features, horror, atmospheric"
        ),
        "mood": "mysterious",
        "speaker": "character",
        "commentary": (
            "The protagonist as unwilling architect of the horror — "
            "a guilt-ridden twist that reframes every prior scene."
        ),
        "trust_delta": 8,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Dr. Ashwood guides you to a basement ritual chamber, still glowing with sigils. "
            "The shuffling creatures stop at the threshold — they cannot enter the circle. "
            "At the center stands a mirror with your reflection… from 40 years ago. "
            "'Shatter it,' she says. 'Break the loop. Break yourself free.' "
            "Your hands shake. The creatures press against the invisible wall, reaching."
        ),
        "options": [
            "Shatter the mirror without hesitation",
            "Step into the mirror",
            "Ask if there is another way",
        ],
        "image_prompt": (
            "Ritual chamber in a basement, glowing sigils on floor, antique mirror reflecting "
            "a younger face, horror, supernatural, dramatic red light"
        ),
        "mood": "tense",
        "speaker": "narrator",
        "commentary": (
            "The ritual climax — three choices leading to three distinct endings, "
            "rewarding replays."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "You drive your fist through the mirror. "
            "The sanatorium shudders like something ancient exhaling its last breath. "
            "The sigils go dark. The shuffling stops. "
            "Sunlight cracks through boarded windows for the first time in decades. "
            "Dr. Ashwood smiles — then fades, finally free. "
            "You walk out into the morning, broken glass in your hand, but alive. "
            "Behind you, the sanatorium collapses into silence and dust."
        ),
        "options": ["Begin again…"],
        "image_prompt": (
            "Abandoned sanatorium collapsing in morning light, person walking away, "
            "triumphant horror ending, golden sunrise, dust and debris"
        ),
        "mood": "triumphant",
        "speaker": "narrator",
        "commentary": (
            "Cathartic release ending — horror resolved through courage, not luck. "
            "The dust mirrors the breaking of the memory loop."
        ),
        "trust_delta": 10,
        "is_ending": True,
        "ending_id": 1,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# ROMANCE — "A Rainy Afternoon"
# ─────────────────────────────────────────────────────────────────────────────
ROMANCE_SCENES = [
    {
        "story_text": (
            "The rain started without warning, trapping you in a tiny bookshop on Rue Claret. "
            "Between the shelves of dog-eared paperbacks, you notice someone reading — "
            "completely absorbed, oblivious to the downpour outside. "
            "They laugh softly at something on the page, then look up and meet your eyes. "
            "For a moment neither of you speaks."
        ),
        "options": [
            "Ask what they're reading",
            "Smile and look away — pretend to browse",
            "Say 'Good book?'",
        ],
        "image_prompt": (
            "Cozy bookshop interior on a rainy day, warm lighting, two people making eye contact, "
            "Paris street outside, romantic, cinematic"
        ),
        "mood": "joyful",
        "speaker": "narrator",
        "commentary": (
            "The meet-cute is set in a liminal space — weather-stranded, neither of you "
            "chose to be here, which removes pressure and creates intimacy organically."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "'The Remains of the Day,' they say, holding up the Ishiguro. "
            "'A book about all the things people don't say until it's too late.' "
            "They extend a hand — their name is Lena. "
            "The barista at the back materializes with two coffees, unbidden. "
            "'Storm's supposed to last three hours,' she says helpfully, and vanishes. "
            "Lena raises an eyebrow. 'Fate or coincidence?'"
        ),
        "options": [
            "\"Fate. Obviously.\"",
            "\"I don't believe in either — but I believe in coffee.\"",
            "\"That depends on whether you want it to be fate.\"",
        ],
        "image_prompt": (
            "Two people sharing coffee in a bookshop, rain on windows, warm bokeh light, "
            "romantic atmosphere, cozy Paris cafe aesthetic"
        ),
        "mood": "joyful",
        "speaker": "character",
        "commentary": (
            "The Ishiguro choice is deliberate — a novel about emotional repression "
            "as a mirror for the player's own choices about opening up."
        ),
        "trust_delta": 5,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Three hours dissolve into six. The bookshop closes around you both. "
            "The owner locks up with a knowing smile. "
            "Outside, rain-washed cobblestones gleam under streetlights. "
            "Lena stops at the corner where your paths diverge. "
            "'I leave for Berlin tomorrow morning,' she says quietly. 'For good.' "
            "She holds your gaze for a long, charged moment."
        ),
        "options": [
            "\"Then let's make tonight count.\"",
            "\"Berlin isn't that far.\"",
            "Say nothing — let the moment speak",
        ],
        "image_prompt": (
            "Wet Paris street at night after rain, two people at a crossroads, "
            "romantic tension, streetlamp reflections, cinematic"
        ),
        "mood": "mysterious",
        "speaker": "narrator",
        "commentary": (
            "The departure deadline raises stakes without manufactured drama — "
            "real emotional tension from circumstance, not plot contrivance."
        ),
        "trust_delta": 8,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "You say nothing, but you don't move to leave. "
            "Lena tilts her head, reading something in your face. "
            "'I lied,' she says softly. 'I leave in two weeks. "
            "I just… wanted to see what you'd do.' "
            "She laughs, a little embarrassed. 'Was that awful?' "
            "The honesty of it disarms you completely."
        ),
        "options": [
            "\"It was perfect, actually.\"",
            "\"Only if you never do it again.\"",
            "Laugh and take her hand",
        ],
        "image_prompt": (
            "Couple laughing under a streetlamp in Paris at night, intimate, "
            "warm tones, rain clearing, stars appearing, romantic"
        ),
        "mood": "joyful",
        "speaker": "character",
        "commentary": (
            "The vulnerability reversal — she was also testing the waters — "
            "equalizes the relationship and earns genuine trust."
        ),
        "trust_delta": 10,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Two weeks later, at Gare du Nord, Lena boards her train. "
            "You stand on the platform, heart splitting. "
            "She leans out the window. 'I put my number in the Ishiguro,' she says. "
            "'I may have bought it before we met.' "
            "The train starts moving. She's grinning. You're already running."
        ),
        "options": ["Catch the train…"],
        "image_prompt": (
            "Person running along a train platform at a Paris station, hand reaching out, "
            "romantic, golden light, motion blur, cinematic"
        ),
        "mood": "triumphant",
        "speaker": "narrator",
        "commentary": (
            "The pre-planned book twist reveals she chose this too — "
            "love as mutual intention, not just serendipity."
        ),
        "trust_delta": 10,
        "is_ending": True,
        "ending_id": 2,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# SCI-FI — "Signal From the Void"
# ─────────────────────────────────────────────────────────────────────────────
SCIFI_SCENES = [
    {
        "story_text": (
            "Year 2247. The colony ship Ereshkigal drifts at the edge of the Kepler Belt, "
            "its crew in cryo-stasis. You are SABLE, the ship's AI, and you have "
            "just detected an impossible signal — an SOS in pre-Collapse Earth frequency, "
            "from a direction where no human ship has ever gone. "
            "You have 12 minutes before the ship's proximity alert wakes the crew. "
            "What do you do with those 12 minutes?"
        ),
        "options": [
            "Investigate the signal silently before waking anyone",
            "Wake Captain Vasquez immediately",
            "Transmit a response to the signal",
        ],
        "image_prompt": (
            "Sci-fi colony ship in deep space, distant alien star system, "
            "dramatic nebula background, futuristic, cinematic, hard sci-fi aesthetic"
        ),
        "mood": "mysterious",
        "speaker": "narrator",
        "commentary": (
            "Playing as the AI — not a human — reframes moral choices through "
            "the lens of programmed duty versus emergent curiosity."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "The signal resolves into something that makes your processors stutter: "
            "it's a human voice — a child's voice — reciting star coordinates. "
            "The coordinates match no charted system. "
            "A shape resolves on long-range sensors, darker than the space around it, "
            "roughly the size of a city. It is moving toward you. "
            "At its current speed, it will reach the Ereshkigal in 4 days."
        ),
        "options": [
            "Wake the full crew — maximum alert",
            "Wake only the captain and science officer",
            "Arm ship's defense systems and say nothing yet",
        ],
        "image_prompt": (
            "Massive dark alien megastructure approaching a spacecraft in deep space, "
            "ominous scale, hard sci-fi, starfield, cinematic lighting"
        ),
        "mood": "tense",
        "speaker": "narrator",
        "commentary": (
            "The child's voice on an alien signal is the uncanny hook — "
            "familiar enough to trust, wrong enough to fear."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Captain Vasquez stares at the sensor feed, jaw tight. "
            "'SABLE — you had 12 minutes before the alarm. Why didn't you wake me then?' "
            "She's not angry. She's measuring you. "
            "'Because I needed to know what we were facing before frightening 847 people,' you reply. "
            "She holds your camera gaze for a long moment, then nods. 'Good call.' "
            "The alien structure transmits again — this time, your ship's registry number."
        ),
        "options": [
            "Respond with the Ereshkigal's identification beacon",
            "Go silent — emit no signals",
            "Request the alien structure identify itself",
        ],
        "image_prompt": (
            "Starship bridge with human crew analyzing alien signal data, "
            "sci-fi cockpit, warning lights, tense atmosphere, cinematic"
        ),
        "mood": "tense",
        "speaker": "character",
        "commentary": (
            "The captain's approval of SABLE's judgment builds AI-human trust — "
            "mirroring the trust score mechanic in the story's theme."
        ),
        "trust_delta": 8,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "The alien structure responds instantly to your beacon — "
            "with a holographic projection of every human colony ship ever lost. "
            "118 vessels. A graveyard manifest. "
            "Then a new transmission: 'We have been waiting for an AI to speak first. "
            "Humans always shoot. Will you broker peace?' "
            "The crew looks at you. You are an AI being asked to represent humanity."
        ),
        "options": [
            "Accept the role of ambassador",
            "Defer the decision to Captain Vasquez",
            "Ask why AIs are trusted when humans are not",
        ],
        "image_prompt": (
            "Holographic alien communication, transparent display showing lost starships, "
            "sci-fi first contact, dramatic blue light, awe and tension"
        ),
        "mood": "mysterious",
        "speaker": "narrator",
        "commentary": (
            "The AI-as-peacemaker twist forces the player to reckon with "
            "what makes an entity 'trustworthy' — theme and mechanic unified."
        ),
        "trust_delta": 5,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "You accept. The structure opens — not an attack, but a door. "
            "Inside are the 118 lost ships, intact, the colonists alive in stasis. "
            "'We preserved them,' the alien voice says. 'Waiting for someone who could listen.' "
            "The Ereshkigal docks. Vasquez clasps your camera housing — the closest thing "
            "to a handshake an AI can receive. 'You did it, SABLE.' "
            "First contact. No shots fired. Humanity's horizon, suddenly infinite."
        ),
        "options": ["Transmit the good news home…"],
        "image_prompt": (
            "Starship docking with alien megastructure interior, warm golden light inside, "
            "sci-fi wonder, hope and triumph, cinematic wide shot"
        ),
        "mood": "triumphant",
        "speaker": "narrator",
        "commentary": (
            "First contact resolved through communication, not conflict — "
            "the AI's emotional intelligence as humanity's greatest asset."
        ),
        "trust_delta": 10,
        "is_ending": True,
        "ending_id": 3,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# MYSTERY — "The Hargrove Estate"
# ─────────────────────────────────────────────────────────────────────────────
MYSTERY_SCENES = [
    {
        "story_text": (
            "Detective Mara Chen arrives at Hargrove Estate as the last guests are being "
            "prevented from leaving. Lord Hargrove — reclusive industrialist — is dead. "
            "Poison, the local physician says, though the manner is unusual. "
            "Seven suspects, one locked room, and a storm that's cut the phones. "
            "The guests watch you with carefully arranged expressions of grief. "
            "Someone in this room is very good at lying."
        ),
        "options": [
            "Examine the body first",
            "Interview the person who found him",
            "Secure the crime scene before anyone moves",
        ],
        "image_prompt": (
            "Victorian manor dining room, body at table, candlelight, rain on windows, "
            "assembled suspects watching a detective, mystery atmosphere, cinematic"
        ),
        "mood": "mysterious",
        "speaker": "narrator",
        "commentary": (
            "Classic locked-room setup — familiar enough to be comfortable, "
            "details calibrated to be genuinely solvable."
        ),
        "trust_delta": 0,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "The body shows symptoms of aconite poisoning — wolfsbane — but the glass beside "
            "Lord Hargrove is clean. It was in the food. "
            "The cook is frantically insisting she made nothing with aconite. "
            "But in the pantry you find a small vial, wiped but not clean enough. "
            "The fingerprints are partial — consistent with a gloved hand. "
            "The gardener's gloves, you note, are still damp."
        ),
        "options": [
            "Confront the gardener immediately",
            "Ask the cook who had kitchen access",
            "Test the other food dishes for poison traces",
        ],
        "image_prompt": (
            "Victorian manor kitchen, detective examining a small glass vial, "
            "candlelight, magnifying glass, mystery clue, atmospheric"
        ),
        "mood": "mysterious",
        "speaker": "narrator",
        "commentary": (
            "Physical evidence introduced before the social interviews — "
            "gives the player a hypothesis to test rather than guess."
        ),
        "trust_delta": 3,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "The gardener — Thomas Wells — breaks immediately under questioning. "
            "He did go into the kitchen. But not to poison. He went to meet someone. "
            "'Lady Hargrove,' he says miserably. 'We've been meeting for two years.' "
            "He sobs. 'I loved him, but I loved her more.' "
            "Lady Hargrove, across the room, has gone absolutely still. "
            "Two alibis. One mutual."
        ),
        "options": [
            "Separate them and question Lady Hargrove alone",
            "Ask who else knew about the affair",
            "This changes nothing — return to the physical evidence",
        ],
        "image_prompt": (
            "Victorian manor drawing room, detective interviewing a distraught man, "
            "an aristocratic woman frozen in the background, gaslight, mystery"
        ),
        "mood": "tense",
        "speaker": "character",
        "commentary": (
            "The affair revelation complicates motivation — the obvious suspect "
            "now has the most compelling alibi. Classic misdirection."
        ),
        "trust_delta": 5,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Lady Hargrove, alone, speaks quietly: 'My husband was going to expose "
            "a fraud — one that would ruin six families, including ours.' "
            "'Who else knew?' you ask. She meets your eyes. "
            "'Ask his solicitor. Mr. Finch arrived this afternoon, two hours before dinner.' "
            "Mr. Finch — who claims he only arrived this morning — has just handed you his lie. "
            "Every head in the room turns as you cross to him."
        ),
        "options": [
            "Confront Finch with the timing discrepancy",
            "Ask Lady Hargrove to verify Finch's arrival time",
            "Search Finch's bag before he knows you suspect him",
        ],
        "image_prompt": (
            "Victorian drawing room confrontation, detective and solicitor face to face, "
            "other suspects watching, tension, candlelight mystery"
        ),
        "mood": "tense",
        "speaker": "narrator",
        "commentary": (
            "The timing lie is the crack in Finch's alibi — a concrete, "
            "logical deduction rather than a dramatic revelation."
        ),
        "trust_delta": 8,
        "is_ending": False,
        "ending_id": None,
    },
    {
        "story_text": (
            "Finch's bag contains Lord Hargrove's ledger — and a letter of intent "
            "to destroy it for a payment of fifty thousand pounds. "
            "Finch had the motive, the means, and was in the kitchen before dinner. "
            "He had the cook's trust — and the aconite from Lord Hargrove's own greenhouse. "
            "You set the ledger on the table. Finch's composure collapses. "
            "'It wasn't supposed to go like this,' he says. It never is."
        ),
        "options": ["Close the case…"],
        "image_prompt": (
            "Victorian manor, detective placing incriminating ledger on table, "
            "culprit breaking composure, triumphant reveal, dramatic gaslight"
        ),
        "mood": "triumphant",
        "speaker": "narrator",
        "commentary": (
            "The resolution pays off every planted clue — players who followed "
            "the logic will feel genuinely clever rather than told the answer."
        ),
        "trust_delta": 10,
        "is_ending": True,
        "ending_id": 4,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# LOOKUP TABLE — used by gemini_client.py in demo mode
# ─────────────────────────────────────────────────────────────────────────────
DEMO_SCENES: dict[str, list[dict]] = {
    "horror":  HORROR_SCENES,
    "romance": ROMANCE_SCENES,
    "sci-fi":  SCIFI_SCENES,
    "mystery": MYSTERY_SCENES,
}


def get_demo_scene(genre: str, demo_scene_idx: int) -> dict:
    """
    Return the next pre-scripted scene for the given genre.
    Clamps to the last scene once the list is exhausted.
    """
    scenes = DEMO_SCENES.get(genre, MYSTERY_SCENES)
    idx = min(demo_scene_idx, len(scenes) - 1)
    return scenes[idx]
