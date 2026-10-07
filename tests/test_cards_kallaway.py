"""The Kallaway-language card kinds (keyline, deck, annotate), adopted 2026-10-06.

What these pin is what would fail silently or look wrong without an error:

1. A keyline has NO glass, so its mask must be empty; a full-frame kind (deck, annotate) must
   cover the whole stage in both passes, or the frosted backdrop would show a hard edge.
2. The deck is centred on the CURRENT chapter, every visible card sits fully inside the frame,
   and the hand-over (previous lit -> done, current next -> lit) happens on the seam's phrase.
3. An annotate mark is given in fractions of the IMAGE and must land on the image as fitted;
   lateral callouts narrow the image so a label never runs off the frame.
4. The new kinds use the brand's `glow`, not `accent`, so the existing cards keep their colour.
"""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

HELPERS = Path(__file__).parents[1] / "helpers"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HELPERS / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cards = _load("video_use_cards_k", "cards.py")

SPOKEN = ("so here is the thing confidence is the memory of proof not a feeling you wait for "
          "now second my mind is where the work happens look at my thumbnail my face is here "
          "and the expression matters and the views tell you everything that is the lesson okay")


class _Edit:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "transcripts").mkdir()
        self.words = [{"type": "word", "text": t, "start": 0.6 + i * 0.32, "end": 0.9 + i * 0.32}
                      for i, t in enumerate(SPOKEN.split())]
        (self.dir / "transcripts" / "A.json").write_text(json.dumps({"words": self.words}))
        self.edl = {"ranges": [{"source": "A", "start": 0, "end": 30}], "sources": {"A": "a.mp4"},
                    "decks": {"pillars": [{"title": "Body", "icon": "bolt"}, {"title": "Mind"},
                                          {"title": "Voice"}]}}
        self.durs = [30.0]
        # a 400x200 test image (aspect 2:1)
        self.img = self.dir / "img.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=gray:s=400x200", "-frames:v", "1", str(self.img)], check=True)

    def t(self, word):
        return next(w["start"] for w in self.words if w["text"] == word)

    def resolve(self, card, w=1920, h=1080):
        return cards.resolve([card], self.edl, self.dir, self.durs, w, h)[0]


KEY = {"id": "k", "kind": "keyline", "text": "Confidence is the memory of proof",
       "sub": "Not a feeling", "at": "memory of proof"}


class KeylineTests(unittest.TestCase):
    def setUp(self):
        self.e = _Edit()

    def test_lands_as_its_phrase_is_said(self):
        s = self.e.resolve(KEY)
        self.assertAlmostEqual(s["start"] + s["in"], self.e.t("memory") - cards.LEAD, places=2)

    def test_mask_is_empty_because_a_keyline_has_no_glass(self):
        s = self.e.resolve(KEY)
        self.assertIn("kl-text", cards.page(s, "overlay", 1920, 1080))
        mask = cards.page(s, "mask", 1920, 1080)
        self.assertIn('C.kind === "keyline" ? ""', mask)   # the runtime branch that draws nothing

    def test_typing_time_grows_with_length_but_is_bounded(self):
        short = self.e.resolve({**KEY, "text": "Proof"})["keyline"]["type_dur"]
        long = self.e.resolve({**KEY, "text": "Confidence is the memory of proof, collected daily"})["keyline"]["type_dur"]
        self.assertLess(short, long)
        self.assertGreaterEqual(short, 0.45)
        self.assertLessEqual(long, 1.4)

    def test_one_sentence_only(self):
        with self.assertRaises(cards.CardError):
            self.e.resolve({**KEY, "text": "x " * 60})
        with self.assertRaises(cards.CardError):
            self.e.resolve({**KEY, "text": ""})
        with self.assertRaises(cards.CardError):
            self.e.resolve({**KEY, "scale": 0.6})

    def test_default_sits_above_a_two_line_house_caption(self):
        # house captions: MarginV=30, FontSize=15 on PlayResY 288 -> top of a 2-line cue ~856
        s = self.e.resolve(KEY)
        self.assertLessEqual(s["keyline"]["bottom"], 830)

    def test_low_placement_is_for_cuts_without_burned_captions(self):
        s = self.e.resolve({**KEY, "placement": "low"})
        self.assertGreater(s["keyline"]["bottom"], 900)
        self.assertLessEqual(s["keyline"]["bottom"], 1016)
        with self.assertRaises(cards.CardError):
            self.e.resolve({**KEY, "placement": "middle"})


DECK = {"id": "d", "kind": "deck", "deck": "pillars", "current": 1, "prefix": "Pillar",
        "at": "second my mind"}


class DeckTests(unittest.TestCase):
    def setUp(self):
        self.e = _Edit()

    def test_current_card_is_centred_and_all_cards_fit(self):
        s = self.e.resolve(DECK)
        D = s["deck"]
        cur = next(c for c in D["cards"] if c["k"] == 1)
        self.assertAlmostEqual(cur["x"] + D["w"] / 2, s["stage"]["w"] / 2, places=2)
        for c in D["cards"]:
            self.assertGreaterEqual(c["x"], 0)
            self.assertLessEqual(c["x"] + D["w"], s["stage"]["w"])

    def test_hand_over_previous_lit_to_done_and_current_to_lit(self):
        D = self.e.resolve(DECK)["deck"]
        st = {c["k"]: (c["before"], c["after"]) for c in D["cards"]}
        self.assertEqual(st[0], ("lit", "done"))
        self.assertEqual(st[1], ("next", "lit"))
        self.assertEqual(st[2], ("next", "next"))

    def test_the_light_lands_on_the_phrase(self):
        s = self.e.resolve(DECK)
        self.assertAlmostEqual(s["start"] + s["deck"]["t_light"], self.e.t("second") - cards.LEAD, places=2)

    def test_full_frame_box_in_both_passes(self):
        s = self.e.resolve(DECK)
        self.assertEqual((s["box"]["x"], s["box"]["y"], s["box"]["w"], s["box"]["h0"]),
                         (0, 0, s["stage"]["w"], 1080))
        self.assertEqual(s["kind"], "deck")
        self.assertIn("card.classList.add(\"full\")", cards.page(s, "mask", 1920, 1080))

    def test_only_a_window_of_chapters_is_shown(self):
        e = self.e
        e.edl["decks"]["nine"] = [{"title": f"L{i}"} for i in range(9)]
        D = e.resolve({**DECK, "deck": "nine", "current": 5})["deck"]
        self.assertEqual([c["k"] for c in D["cards"]], [3, 4, 5, 6, 7])

    def test_inline_chapters_and_bad_decks(self):
        s = self.e.resolve({**DECK, "deck": None, "chapters": [{"title": "A"}, {"title": "B"}], "current": 0})
        self.assertEqual(s["deck"]["cards"][0]["after"], "lit")
        for bad in ({"deck": "nope"}, {"current": 3}, {"current": -1},
                    {"deck": None, "chapters": [{"title": "only one"}]},
                    {"deck": None, "chapters": [{"title": "A"}, {"title": ""}]},
                    {"deck": None, "chapters": [{"title": "A", "icon": "nope"}, {"title": "B"}]}):
            with self.assertRaises(cards.CardError):
                self.e.resolve({**DECK, **bad})


class AnnotateTests(unittest.TestCase):
    def setUp(self):
        self.e = _Edit()
        self.card = {"id": "a", "kind": "annotate", "image": str(self.e.img), "at": "look at my thumbnail",
                     "title": "3 elements",
                     "marks": [{"type": "box", "rect": [0.25, 0.5, 0.5, 0.5], "at": "my face"},
                               {"type": "highlight", "rect": [0, 0, 1, 0.1], "at": "the views"}]}

    def test_marks_are_image_fractions_mapped_onto_the_fitted_image(self):
        A = self.e.resolve(self.card)["annotate"]
        I, m = A["image"], A["marks"][0]
        self.assertAlmostEqual(I["w"] / I["h"], 2.0, places=2)
        self.assertAlmostEqual(m["x"], I["x"] + 0.25 * I["w"], places=2)
        self.assertAlmostEqual(m["y"], I["y"] + 0.5 * I["h"], places=2)
        self.assertAlmostEqual(m["w"], 0.5 * I["w"], places=2)

    def test_each_mark_lands_on_its_own_phrase(self):
        s = self.e.resolve(self.card)
        self.assertAlmostEqual(s["start"] + s["annotate"]["marks"][0]["t"], self.e.t("face") - 0.32 - cards.LEAD, places=2)

    def test_lateral_callouts_narrow_the_image_so_labels_fit(self):
        plain = self.e.resolve(self.card)["annotate"]["image"]["w"]
        call = {**self.card, "marks": [{"type": "callout", "rect": [0.5, 0.2, 0.2, 0.2], "label": "Facial expression",
                                        "side": "right", "at": "expression"}]}
        A = self.e.resolve(call)["annotate"]
        self.assertLess(A["image"]["w"], plain)
        x2 = A["marks"][0]["line"][2]
        self.assertLess(x2 + 300, 1920)      # room for a label to the right

    def test_image_is_inlined_at_the_pixels_it_occupies(self):
        A = self.e.resolve(self.card, 3840, 2160)["annotate"]
        self.assertTrue(A["image"]["src"].startswith("data:image/png;base64,"))

    def test_bad_annotations_raise(self):
        for over in ({"image": "missing.png"}, {"at": None},
                     {"marks": [{"type": "circle", "rect": [0, 0, 1, 1], "at": "my face"}]},
                     {"marks": [{"type": "box", "rect": [0.5, 0.5, 0.6, 0.2], "at": "my face"}]},
                     {"marks": [{"type": "callout", "rect": [0, 0, 1, 1], "at": "my face"}]},
                     {"marks": [{"type": "callout", "rect": [0, 0, 1, 1], "label": "x", "side": "up", "at": "my face"}]}):
            with self.assertRaises(cards.CardError):
                self.e.resolve({**self.card, **over})


class ColourTests(unittest.TestCase):
    def test_new_kinds_use_glow_and_old_accent_is_untouched(self):
        e = _Edit()
        (e.dir / "brand.json").write_text(json.dumps({"accent": "#F25435", "glow": "#7C3AED"}))
        s = e.resolve(KEY)
        html = cards.page(s, "overlay", 1920, 1080)
        self.assertIn("--glow: #7C3AED", html)
        self.assertIn("--accent: #F25435", html)

    def test_glow_defaults_to_violet(self):
        self.assertEqual(cards.DEFAULT_BRAND["glow"], "#8B5CF6")


if __name__ == "__main__":
    unittest.main()
