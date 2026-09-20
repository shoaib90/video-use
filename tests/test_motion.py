"""Motion engine and components.

The reference video's motion principles are timing, weight, rhythm and
intention, and the failure these tests exist to prevent is the one that made a
first hand-rolled attempt read as amateur: every element animating identically.
Plus the two bugs that cost a render each - a relative duration compared
against an absolute clock, and type with no fit running off the canvas.
"""
import importlib.util
import sys
import unittest
from pathlib import Path

HELPERS = Path(__file__).parents[1] / "helpers"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HELPERS / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mo = _load("video_use_motion", "motion.py")
brand_mod = _load("video_use_brand", "brand.py")
comp = _load("video_use_components", "components.py")
Brand = brand_mod.Brand


class CurveTests(unittest.TestCase):
    def test_every_curve_starts_at_zero_and_lands_on_one(self):
        for name, fn in mo.CURVES.items():
            self.assertAlmostEqual(fn(0.0), 0.0, places=5, msg=name)
            self.assertAlmostEqual(fn(1.0), 1.0, places=3, msg=name)

    def test_back_out_actually_overshoots(self):
        # the overshoot is what gives an element mass; without it this is a fade
        self.assertGreater(max(mo.back_out(t / 100) for t in range(101)), 1.0)

    def test_anticipate_pulls_back_first(self):
        self.assertLess(min(mo.anticipate(t / 100) for t in range(101)), 0.0)

    def test_spring_oscillates_then_settles(self):
        vals = [mo.spring(t / 200) for t in range(201)]
        self.assertGreater(max(vals), 1.0)
        self.assertAlmostEqual(vals[-1], 1.0, places=3)


class WeightTests(unittest.TestCase):
    def test_roles_are_actually_distinct(self):
        """'A logo landing and a subtitle fading should not feel the same.'"""
        hero, aside = mo.WEIGHTS["hero"], mo.WEIGHTS["aside"]
        self.assertGreater(hero.duration, aside.duration)
        self.assertGreater(abs(hero.travel), abs(aside.travel))
        self.assertNotEqual(hero.curve, aside.curve)
        self.assertTrue(hero.blur)
        self.assertFalse(aside.blur)

    def test_weight_is_anchored_to_its_own_start(self):
        w = mo.WEIGHTS["primary"]
        self.assertAlmostEqual(w.at(5.0, start=5.0), 0.0, places=9)
        self.assertAlmostEqual(w.at(5.0 + w.duration, start=5.0), 1.0, places=3)

    def test_stagger_accelerates_when_biased(self):
        even = [mo.stagger(i, 0.1, 1.0) for i in range(4)]
        biased = [mo.stagger(i, 0.1, 1.4) for i in range(4)]
        self.assertAlmostEqual(even[1] - even[0], even[3] - even[2], places=6)
        self.assertGreater(biased[3] - biased[2], biased[1] - biased[0])


class ComponentTimingTests(unittest.TestCase):
    """The bug that cost a whole render: a component placed 11s into the
    timeline took a RELATIVE duration, compared it against an ABSOLUTE t,
    concluded its exit fade was long finished, and silently drew nothing."""

    def setUp(self):
        self.b = Brand()

    def test_component_live_late_in_the_timeline(self):
        c = comp.build("kinetic_type", self.b, 1080,
                       {"words": [{"text": "hi", "x": 0.1, "y": 0.5}]},
                       start=11.0, end=13.5)
        self.assertEqual(c._out(10.0), 1.0)       # before it ends
        self.assertEqual(c._out(12.0), 1.0)       # live
        self.assertEqual(c._out(13.5), 0.0)       # gone
        self.assertTrue(0.0 < c._out(13.3) < 1.0)  # mid-fade

    def test_it_actually_paints_late_in_the_timeline(self):
        from PIL import Image
        c = comp.build("kinetic_type", self.b, 1080,
                       {"words": [{"text": "MOMENT", "x": 0.05, "y": 0.4,
                                   "role": "hero"}],
                        "times": [11.0]},
                       start=11.0, end=13.5)
        img = Image.new("RGBA", (600, 300), (0, 0, 0, 0))
        c.draw(img, 12.0)
        self.assertGreater(img.getchannel("A").getextrema()[1], 200,
                           "component drew nothing at a time it should be live")


class FitTests(unittest.TestCase):
    def setUp(self):
        self.b = Brand()

    def test_long_line_is_shrunk_to_fit_with_room_for_its_shadow(self):
        from PIL import Image, ImageDraw
        items = ["CONSTANTLY AFRAID OF FAILING"]
        c = comp.build("staggered_items", self.b, 2160, {"items": items},
                       start=0, end=5)
        base = self.b.px(self.b.size_title, 2160)
        fitted = c.fit_size(items, base, 1420)
        self.assertLess(fitted, base)
        d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
        f = comp.load_font(self.b, "light", fitted)
        w = comp.text_width(d, f, items[0], fitted * self.b.tracking)
        self.assertLessEqual(w, 1420 - c.pad * 3)

    def test_kinetic_word_fits_the_width_right_of_its_anchor(self):
        from PIL import Image
        img = Image.new("RGBA", (1420, 900), (0, 0, 0, 0))
        c = comp.build("kinetic_type", self.b, 2160,
                       {"words": [{"text": "FOR MY MOMENT", "scale": 1.55,
                                   "x": 0.04, "y": 0.4, "role": "hero"}],
                        "times": [0.0]}, start=0.0, end=4.0)
        c.draw(img, 1.2)
        # nothing may touch the last column, or it has been clipped
        edge = img.crop((img.width - 2, 0, img.width, img.height))
        self.assertEqual(edge.getchannel("A").getextrema()[1], 0)


class BrandTests(unittest.TestCase):
    def test_sizes_are_fractions_so_one_brand_serves_every_resolution(self):
        b = Brand()
        self.assertEqual(b.px(b.size_title, 2160), 3 * b.px(b.size_title, 720))

    def test_roundtrip(self):
        import tempfile
        b = Brand(accent="#123456")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "brand.json"
            b.save(p)
            self.assertEqual(Brand.load(p).accent, "#123456")

    def test_unknown_keys_in_a_saved_brand_do_not_break_loading(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "b.json"
            p.write_text(json.dumps({"accent": "#ABCDEF", "future_field": 1}))
            self.assertEqual(Brand.load(p).accent, "#ABCDEF")


class IntlFaceTests(unittest.TestCase):
    def test_non_latin_selects_the_international_face(self):
        # PIL, like drawtext, draws a blank box rather than falling back
        self.assertTrue(comp.needs_intl("बढ़िया"))
        self.assertFalse(comp.needs_intl("CONFUSED"))


if __name__ == "__main__":
    unittest.main()


class DemotionTests(unittest.TestCase):
    """Shrinking the talking head so a graphic can own the frame."""

    def setUp(self):
        self.render = _load("video_use_render_dem", "render.py")

    def test_no_demotions_is_a_no_op(self):
        chain, label = self.render.build_demotion_filter([], "#000000", "30")
        self.assertEqual(chain, "")
        self.assertEqual(label, "[0:v]")

    def test_uses_overlay_not_pad_for_placement(self):
        """`pad` evaluates x/y ONCE at configuration time, so the picture
        shrinks towards the top-left and never re-centres. Measured, not
        assumed - the first attempt used pad and did exactly that."""
        chain, _ = self.render.build_demotion_filter(
            [{"start": 2.0, "end": 6.0, "scale": 0.4, "anchor": "right"}],
            "#101014", "30")
        self.assertIn("overlay=", chain)
        self.assertNotIn("pad=", chain)

    def test_both_scale_and_placement_are_evaluated_per_frame(self):
        chain, _ = self.render.build_demotion_filter(
            [{"start": 1.0, "end": 5.0}], "#000000", "30")
        self.assertEqual(chain.count("eval=frame"), 2,
                         "scale and overlay must BOTH re-evaluate per frame")

    def test_output_dimensions_stay_even(self):
        # an odd dimension fails to encode in yuv420p
        chain, _ = self.render.build_demotion_filter(
            [{"start": 1.0, "end": 5.0}], "#000000", "30")
        self.assertIn("2*floor(iw*", chain)
        self.assertIn("2*floor(ih*", chain)

    def test_anchor_names_resolve(self):
        for name, frac in (("right", 0.72), ("left", 0.28), ("center", 0.5)):
            self.assertEqual(self.render.ANCHORS[name], frac)

    def test_envelope_is_zero_outside_and_one_inside(self):
        def smoothstep(u):
            u = max(0.0, min(1.0, u))
            return u * u * (3 - 2 * u)

        a, b, tau = 2.0, 8.0, 0.5

        def f(t):
            return smoothstep((t - a) / tau) - smoothstep((t - (b - tau)) / tau)

        self.assertAlmostEqual(f(1.0), 0.0, places=6)     # before
        self.assertAlmostEqual(f(5.0), 1.0, places=6)     # inside
        self.assertAlmostEqual(f(9.0), 0.0, places=6)     # after
        self.assertTrue(0 < f(a + tau / 2) < 1)           # easing in
        self.assertTrue(0 < f(b - tau / 2) < 1)           # easing out


class PILBlendingTests(unittest.TestCase):
    def test_imagedraw_replaces_rather_than_blends(self):
        """Pinning a property of PIL that misled a whole preview round.

        `ImageDraw` does NOT alpha-blend onto an RGBA image - it writes the
        RGBA value straight in, even with `Draw(img, "RGBA")`. So a 9%-alpha
        element drawn onto an opaque background previews as 100% opaque, and a
        graphic that is correct in the real pipeline (transparent canvas, then
        ffmpeg composites) looks broken in a naive preview.

        Preview by alpha_compositing the transparent layer onto a background,
        the way ffmpeg does.
        """
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 255))
        ImageDraw.Draw(img).rectangle([0, 0, 7, 7], fill=(255, 255, 255, 25))
        self.assertEqual(img.getpixel((4, 4)), (255, 255, 255, 25))

        layer = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle([0, 0, 7, 7], fill=(255, 255, 255, 25))
        composited = Image.alpha_composite(Image.new("RGBA", (8, 8), (0, 0, 0, 255)),
                                           layer)
        self.assertLess(composited.getpixel((4, 4))[0], 40)


class CarouselTests(unittest.TestCase):
    def test_neighbours_stay_in_frame(self):
        """A carousel whose columns are wider than the frame shows one item at
        a time, which reads as unrelated cards rather than a list."""
        from PIL import Image
        b = Brand()
        items = [{"title": f"Item {i}", "bullets": ["a", "b"]} for i in range(5)]
        c = comp.build("list_carousel", b, 2160,
                       {"items": items, "times": [0.0, 2.0, 4.0, 6.0, 8.0]},
                       start=0.0, end=10.0)
        img = Image.new("RGBA", (3840, 1100), (0, 0, 0, 0))
        c.draw(img, 4.6)                       # settled on item 3 of 5
        alpha = img.getchannel("A")
        left = alpha.crop((0, 0, 500, 1100)).getextrema()[1]
        right = alpha.crop((3340, 0, 3840, 1100)).getextrema()[1]
        self.assertGreater(left, 0, "no neighbour visible to the left")
        self.assertGreater(right, 0, "no neighbour visible to the right")

    def test_list_carousel_maps_to_the_sliding_treatment(self):
        self.assertIs(comp.REGISTRY["list_carousel"], comp.SlidingCarousel)


class SubjectMaskingTests(unittest.TestCase):
    """A graphic passing BEHIND the speaker."""

    def setUp(self):
        self.render = _load("video_use_render_mask", "render.py")
        self.matte = _load("video_use_matte", "matte.py")
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        (self.d / "base.mp4").write_text("")
        (self.d / "m.mp4").write_text("")

    def _graph(self, overlays, matte=None):
        cap = {}
        orig = self.render.subprocess.run

        def fake(cmd, **kw):
            if isinstance(cmd, list) and "-filter_complex" in cmd:
                cap["fc"] = cmd[cmd.index("-filter_complex") + 1]

            class R:
                returncode = 0
                stdout = stderr = ""
            return R()

        self.render.subprocess.run = fake
        try:
            self.render.build_final_composite(
                self.d / "base.mp4", overlays, None, self.d / "o.mp4", self.d,
                matte=matte)
        finally:
            self.render.subprocess.run = orig
        return cap.get("fc", "")

    def test_behind_subject_without_a_matte_is_refused(self):
        """Silently ignoring it would render the graphic ON TOP of the speaker,
        which is the opposite of what was asked for."""
        with self.assertRaises(ValueError):
            self._graph([{"file": "a.mov", "start_in_output": 0, "duration": 2,
                          "behind_subject": True}])

    def test_subject_is_recomposited_after_behind_and_before_front(self):
        fc = self._graph(
            [{"file": "front.mov", "start_in_output": 0, "duration": 2},
             {"file": "back.mov", "start_in_output": 0, "duration": 2,
              "behind_subject": True}],
            matte=self.d / "m.mp4")
        self.assertIn("alphamerge", fc)
        # the behind overlay is chained first, then the subject goes back on top
        self.assertLess(fc.index("[b_main][1:v]overlay"), fc.index("alphamerge"))
        self.assertLess(fc.index("alphamerge"), fc.index("[2:v]overlay"))

    def test_scale2ref_is_given_both_inputs(self):
        """scale2ref scales its FIRST input to match its SECOND and returns
        both; calling it with one input is a filtergraph error."""
        fc = self._graph([{"file": "b.mov", "start_in_output": 0, "duration": 2,
                           "behind_subject": True}], matte=self.d / "m.mp4")
        seg = [p for p in fc.split(";") if "scale2ref" in p][0]
        self.assertEqual(seg.count("["), 4, f"scale2ref needs 2 in + 2 out: {seg}")

    def test_no_matte_means_no_split_and_no_alphamerge(self):
        fc = self._graph([{"file": "a.mov", "start_in_output": 0, "duration": 2}])
        self.assertNotIn("alphamerge", fc)
        self.assertNotIn("split[b_main]", fc)

    def test_worker_source_is_valid_python(self):
        compile(self.matte.WORKER, "<worker>", "exec")

    def test_matte_defaults_err_outward(self):
        """A matte that is slightly generous hides a seam; one that is slightly
        tight eats into the shoulder."""
        import inspect
        sig = inspect.signature(self.matte.build_matte)
        self.assertGreater(sig.parameters["dilate"].default, 0)
        self.assertGreater(sig.parameters["smooth"].default, 0)


class NodeDiagramTests(unittest.TestCase):
    """Nodes appearing in sequence with connections drawing themselves."""

    def setUp(self):
        self.b = Brand()
        self.nodes = [{"title": "Basic", "subtitle": "After Effects"},
                      {"title": "Intermediate", "subtitle": "Illustrator"},
                      {"title": "Advanced", "subtitle": "Figma"}]

    def _c(self, **kw):
        data = {"nodes": self.nodes, "times": [0.0, 2.0, 4.0], **kw}
        return comp.build("node_diagram", self.b, 2160, data, start=0.0, end=8.0)

    def test_registered(self):
        self.assertIn("node_diagram", comp.REGISTRY)

    def test_edges_default_to_a_chain(self):
        from PIL import Image
        c = self._c()
        img = Image.new("RGBA", (2400, 1400), (0, 0, 0, 0))
        c.draw(img, 5.0)
        self.assertGreater(img.getchannel("A").getextrema()[1], 200)

    def test_an_edge_waits_for_BOTH_its_endpoints(self):
        """A line arriving at a node that does not exist yet reads as a glitch.

        Between node 0 appearing and node 1 appearing, only node 0's card may
        be painted - nothing in the region the edge would travel through.
        """
        from PIL import Image
        c = self._c()
        early = Image.new("RGBA", (2400, 1400), (0, 0, 0, 0))
        c.draw(early, 1.2)                      # node 0 up, node 1 not yet
        late = Image.new("RGBA", (2400, 1400), (0, 0, 0, 0))
        c.draw(late, 3.4)                       # both up, edge drawn
        # clear of node 0's own card (which ends at x=713, y=476) so the band
        # only ever contains the edge or node 1
        band = lambda im: im.crop((760, 500, 1500, 900)).getchannel("A").getextrema()[1]
        self.assertEqual(band(early), 0, "an edge was drawn before its target existed")
        self.assertGreater(band(late), 0, "the edge never drew once both nodes existed")

    def test_cards_stay_inside_the_canvas(self):
        from PIL import Image
        c = self._c(nodes=[{"title": "A very long node label indeed"},
                           {"title": "Another rather long one"}],
                    times=[0.0, 1.0])
        img = Image.new("RGBA", (1600, 900), (0, 0, 0, 0))
        c.draw(img, 3.0)
        a = img.getchannel("A")
        for box in ((0, 0, 2, 900), (1598, 0, 1600, 900),
                    (0, 0, 1600, 2), (0, 898, 1600, 900)):
            self.assertEqual(a.crop(box).getextrema()[1], 0,
                             "a card touched the canvas edge and was clipped")

    def test_explicit_positions_are_honoured(self):
        from PIL import Image
        c = self._c(nodes=[{"title": "L", "x": 0.15, "y": 0.5},
                           {"title": "R", "x": 0.85, "y": 0.5}],
                    times=[0.0, 0.0])
        img = Image.new("RGBA", (2000, 800), (0, 0, 0, 0))
        c.draw(img, 2.0)
        a = img.getchannel("A")
        self.assertGreater(a.crop((100, 0, 500, 800)).getextrema()[1], 0)
        self.assertGreater(a.crop((1500, 0, 1900, 800)).getextrema()[1], 0)


class CurveVsSpringTests(unittest.TestCase):
    """Transforms and opacity take different curves.

    A spring on alpha overshoots past fully opaque and then dips back: `hero`
    peaks at 1.205, clamps to 255, and falls to 96% before settling, so the
    element visibly pulses as it arrives.
    """

    def test_transform_may_overshoot_but_alpha_never_does(self):
        for name, w in mo.WEIGHTS.items():
            alphas = [w.alpha_at(i / 60 * w.duration) for i in range(61)]
            self.assertLessEqual(max(alphas), 1.0, f"{name} alpha exceeds 1")
            self.assertGreaterEqual(min(alphas), 0.0, f"{name} alpha below 0")

    def test_alpha_is_monotonic(self):
        for name, w in mo.WEIGHTS.items():
            a = [w.alpha_at(i / 80 * w.duration) for i in range(81)]
            self.assertTrue(all(y >= x - 1e-9 for x, y in zip(a, a[1:])),
                            f"{name} alpha dips during its reveal")

    def test_hero_transform_still_overshoots(self):
        # the fix must not flatten the thing that gives weight its mass
        w = mo.WEIGHTS["hero"]
        self.assertGreater(max(w.at(i / 60 * w.duration) for i in range(61)), 1.05)


class AccentBudgetTests(unittest.TestCase):
    def test_a_list_with_a_heading_and_an_accent_last_uses_accent_once(self):
        """Accent is capped at ~2 visible uses per frame; a heading plus an
        accented final item is already two from a single component."""
        from PIL import Image
        b = Brand()
        c = comp.build("staggered_items", b, 2160,
                       {"items": ["ONE", "TWO"], "times": [0.0, 0.5],
                        "heading": "a heading", "accent_last": True},
                       start=0.0, end=5.0)
        img = Image.new("RGBA", (1600, 900), (0, 0, 0, 0))
        c.draw(img, 2.0)
        accent = comp.rgba(b.accent)[:3]
        px = list(img.convert("RGBA").getdata())
        rows = sum(1 for r, g, bl, al in px if al > 60 and (r, g, bl) == accent)
        self.assertGreater(rows, 0, "the accented item lost its accent")
        # the heading yields to muted, so accent is not used twice
        muted = comp.rgba(b.muted)[:3]
        self.assertGreater(sum(1 for r, g, bl, al in px
                               if al > 60 and (r, g, bl) == muted), 0)
