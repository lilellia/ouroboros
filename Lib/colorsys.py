"""Conversion functions between RGB and other color systems.

Supported color systems:
rgb:    red, green, blue components (float 0-1)
RGB:    red, green, blue components (int 0-255)
hex:    #RRGGBB
hsl:    hue (0-360), saturation (0-1), lightness (0-1)
yiq:    luma, inphase, quadrature (used by NTSC color TV)
ciexyz: X, Y, Z (float 0-1)
oklab:  L, a, b
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast, override

HEX_COLOR_SHORT = re.compile(r"^#?(?P<R>[0-9A-Fa-f])(?P<G>[0-9A-Fa-f])(?P<B>[0-9A-Fa-f])$")
HEX_COLOR_FULL = re.compile(r"^#?(?P<R>[0-9A-Fa-f]{2})(?P<G>[0-9A-Fa-f]{2})(?P<B>[0-9A-Fa-f]{2})$")


def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


class ColorSpace(ABC):
    _registry: ClassVar[dict[str, type[ColorSpace]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        cls._registry[cls.__name__] = cls

        def _conv[C: ColorSpace](self, target: type[C] = cls, /) -> C:
            return self.convert_to(target)

        _conv.__name__ = f"as_{cls.__name__}"
        _conv.__doc__ = f"Return a representation of the color in {cls.__name__}"

        setattr(ColorSpace, f"as_{cls.__name__}", _conv)

    if TYPE_CHECKING:
        # stick these here as stubs for the type checker
        # these are precisely the methods that __init_subclass__ hooks by default
        def as_rgb(self) -> rgb:
            """Return a representation of the color in rgb."""
            ...

        def as_RGB(self) -> RGB:
            """Return a representation of the color in RGB."""
            ...

        def as_hex(self) -> hex:
            """Return a representation of the color in hex."""
            ...

        def as_yiq(self) -> yiq:
            """Return a representation of the color in yiq."""
            ...

        def as_hsl(self) -> hsl:
            """Return a representation of the color in hsl."""
            ...

        def as_ciexyz(self) -> ciexyz:
            """Return a representation of the color in CIE XYZ."""
            ...

        def as_oklab(self) -> oklab:
            """Return a representation of the color in Oklab."""
            ...

    def convert_to[C: ColorSpace](self, target: type[C]) -> C:
        """Return a representation of the color in the given target color space."""
        if target is type(self):
            return cast(C, self)

        return target.__from_rgb__(*self.__rgb__())

    def __iter__(self) -> Generator[Any]:
        return iter(getattr(self, slot) for slot in self.__slots__)

    def __getitem__(self, index: int) -> float:
        return tuple(getattr(self, slot) for slot in self.__slots__)[index]

    @abstractmethod
    def __rgb__(self) -> rgb:
        """Return an (r, g, b) intermediate representation of the color."""

    def as_rgb(self) -> rgb:
        """Return a representation of the color in rgb."""
        return self.__rgb__()

    @classmethod
    @abstractmethod
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        """Construct an instance of the color from an (r, g, b) intermediate representation."""

    def __repr__(self) -> str:
        values = ", ".join(f"{k}={getattr(self, k)!r}" for k in self.__slots__)
        return f"{type(self).__name__}({values})"


@dataclass(frozen=True, slots=True)
class rgb(ColorSpace):
    """(r, g, b) color tuple, with each component being a float [0, 1]."""

    red: float
    green: float
    blue: float

    @override
    def __rgb__(self) -> Self:
        return self

    @classmethod
    @override
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        return cls(r, g, b)


@dataclass(frozen=True, slots=True)
class RGB(ColorSpace):
    """(R, G, B) color tuple, with each component being an integer [0, 255]."""

    red: int
    green: int
    blue: int

    @override
    def __rgb__(self) -> rgb:
        return rgb(self.red / 255, self.green / 255, self.blue / 255)

    @classmethod
    @override
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        return cls(round(r * 255), round(g * 255), round(b * 255))


@dataclass(frozen=True, slots=True)
class hex(ColorSpace):
    """An #RRGGBB color."""

    hex: str
    _red: float = field(init=False, repr=False)
    _green: float = field(init=False, repr=False)
    _blue: float = field(init=False, repr=False)

    @override
    def __iter__(self) -> Generator[Any]:
        # Explicitly override this because ColorSpace.__iter__ is looking at the slots, and we've defined
        # _red, _green, _blue as slots here, and... those shouldn't be iterated over.
        yield self.hex

    def __post_init__(self) -> None:
        """Enforce that the internal string is #RRGGBB."""
        s = self.hex

        if m := HEX_COLOR_SHORT.match(s):
            R, G, B = m.group("R"), m.group("G"), m.group("B")
            s = f"#{R}{R}{G}{G}{B}{B}"

            object.__setattr__(self, "_red", int(f"{R}{R}", 16) / 255)
            object.__setattr__(self, "_green", int(f"{G}{G}", 16) / 255)
            object.__setattr__(self, "_blue", int(f"{B}{B}", 16) / 255)

        elif m := HEX_COLOR_FULL.match(s):
            R, G, B = m.group("R"), m.group("G"), m.group("B")
            s = f"#{s.lstrip('#')}"

            object.__setattr__(self, "_red", int(R, 16) / 255)
            object.__setattr__(self, "_green", int(G, 16) / 255)
            object.__setattr__(self, "_blue", int(B, 16) / 255)

        else:
            raise ValueError(f"invalid hex color: {self.hex}")

        if s != self.hex:
            object.__setattr__(self, "hex", s)

    @override
    def __rgb__(self) -> rgb:
        return rgb(self._red, self._green, self._blue)

    @classmethod
    @override
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        return cls(f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}")


@dataclass(frozen=True, slots=True)
class yiq(ColorSpace):
    """(Y=luma, I, Q) color tuple. 0 <= luma <= 1, -0.5957 <= inphase <= 0.5957, -0.5226 <= quadrature <= 0.5226.
    YIQ is the color space used by the analog NTSC color TV system.

    Y represents the perceived grey level (0=black, 1=white)
    I and Q represent color, which I roughly corresponding to orange/blue contrast and Q ~ purple/green.

    https://en.wikipedia.org/wiki/YIQ
    """

    luma: float
    inphase: float
    quadrature: float

    @override
    def __rgb__(self) -> rgb:
        # There are a few different sets of constants used to convert. This library uses the FCC NTSC standard (1987).
        # https://en.wikipedia.org/wiki/YIQ#FCC_NTSC_Standard_(SMPTE_C)

        r = self.luma + 0.9468822170900693 * self.inphase + 0.6235565819861433 * self.quadrature
        g = self.luma - 0.27478764629897834 * self.inphase - 0.6356910791873801 * self.quadrature
        b = self.luma - 1.1085450346420322 * self.inphase + 1.7090069284064666 * self.quadrature

        r = clamp(r, low=0, high=1)
        g = clamp(g, low=0, high=1)
        b = clamp(b, low=0, high=1)

        return rgb(r, g, b)

    @classmethod
    @override
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        y = 0.30 * r + 0.59 * g + 0.11 * b
        i = 0.74 * (r - y) - 0.27 * (b - y)
        q = 0.48 * (r - y) + 0.41 * (b - y)
        return cls(y, i, q)

    @property
    def y(self) -> float:
        return self.luma

    @property
    def i(self) -> float:
        return self.inphase

    @property
    def q(self) -> float:
        return self.quadrature


@dataclass(frozen=True, slots=True)
class hsl(ColorSpace):
    """hsl color tuple. 0 <= hue < 360, 0 <= saturation <= 1, 0 <= lightness <= 1."""

    hue: float
    saturation: float
    lightness: float

    @override
    def __rgb__(self) -> rgb:
        """https://en.wikipedia.org/wiki/HSL_and_HSV#HSL_to_RGB_alternative

        Given a color with hue H on [0, 360°], saturation S on [0, 1], and lightness L on [0, 1], we first define the function

            f(n) = L - a * max(-1, min(k - 3, 9 - k, 1))

        where k, n are on R[>=0] and:

            k = (n + H/30°) mod 12
            a = S * min(L, 1 - L)

        And output R, G, B values (from [0, 1]^3) are:

            (R, G, B) = (f(0), f(4), f(8))

        The above alternative formulas allow for shorter implementations. In the above formulas the `a mod b` operation also returns
        the fractional part of the module, e.g., `7.4 mod 6 = 1.4`, and k is on [0, 12].
        """

        def _f(n: int) -> float:
            k = (n + self.hue / 30) % 12
            a = self.saturation * min(self.lightness, 1 - self.lightness)
            return self.lightness - a * max(-1, min(k - 3, 9 - k, 1))

        return rgb(red=_f(0), green=_f(4), blue=_f(8))

    @classmethod
    @override
    def __from_rgb__(cls, red: float, green: float, blue: float) -> Self:
        """https://en.wikipedia.org/wiki/HSL_and_HSV"""

        # "More precisely, both hue and chroma in this model are defined with repsect to the hexagonal shape of the projection.
        # The chroma is the proportion of the distance from the origin to the edge of the hexagon. [...] This ratio is the
        # difference between the largest and smallest values among R, G, B in a color. To make our definitions easier to write,
        # we'll define these maximum, minimum, and chroma components as M, m, and C, respectively.
        #
        # M = max(R, G, B)
        # m = min(R, G, B)
        # C = range(R, G, B) = M - m
        #
        # These operations do not require R, G, B values to be normalized to a specific range (e.g., a range of 0-1 works as
        # well as a range of 0-255)."
        maximum = max(red, green, blue)
        minimum = min(red, green, blue)
        chroma = maximum - minimum

        # "The hue is the proportion of the distance around the edge of the hexagon which passes through the projected point,
        # originally measured on the range [0, 1] but now typically measured in degrees [0, 360°). FOr points which project
        # onto the origin in the chromaticity plane (i.e., grays), heu is undefined. Mathematically, this definition of hue
        # is written piecewise:
        #
        #      { undefined            if C = 0
        # H' = { ((G - B)/C) mod 6    if M = R
        #      { ((B - R)/C) + 2      if M = G
        #      { ((R - G)/C) + 4      if M = B
        #
        # H = H' * 60°
        #
        # Sometimes, neutral colors (i.e., with C=0) are assigned a hue of 0° for convenience of representation.
        if chroma == 0:
            hue_prime = 0
        elif maximum == red:
            hue_prime = ((green - blue) / chroma) % 6
        elif maximum == green:
            hue_prime = ((blue - red) / chroma) + 2
        else:  # maximum == blue:
            hue_prime = ((red - green) / chroma) + 4

        hue = 60 * hue_prime

        # "In the HSL 'bi-hexcone' model, lightness is defined as the average of the largest and smallest color components,
        # i.e., the mid-range of the RGB components. This definition also puts the primary and secondary colors into a plane,
        # but a plane passing halfway between white and black. The resulting color solid is a double-cone similar to Ostwald's [...]
        #
        # L = mid(R, G, B) = (1/2) (M + m)"
        lightness = (maximum + minimum) / 2

        # "To solve problems such as these, the HSL and HSV models scale the chroma so that it always fits into the range [0, 1]
        # for every combination of hue and lightness or value, calling the new attribute saturation in both cases. To calculate
        # either, simply divide the chroma by the maximum chroma for that value or lightness.
        #
        # [...]
        #
        # S_L [the HSL model] = { 0                      if L = 1 or L = 0
        #                       { C / (1 - abs(2L - 1))  otherwise
        saturation = 0 if lightness in (0, 1) else chroma / (1 - abs(2 * lightness - 1))

        return cls(hue, saturation, lightness)

    @property
    def h(self) -> float:
        return self.hue

    @property
    def s(self) -> float:
        return self.saturation

    @property
    def l(self) -> float:
        return self.lightness


@dataclass(frozen=True, slots=True)
class ciexyz(ColorSpace):
    """(X, Y, Z) CIE XYZ color tuple. Each is a float on [0, 1]."""

    x: float
    y: float
    z: float

    @override
    def __rgb__(self) -> rgb:
        """https://www.oceanopticsbook.info/view/photometry-and-visibility/from-xyz-to-rgb"""
        # [R]   [ 3.2404542  -1.5371385  -0.4985314] [X]
        # [G] = [-0.9692660   1.8760108   0.0415560] [Y]
        # [B]   [ 0.0556434  -0.2040259   1.0572252] [Z]
        r = 3.2404542 * self.x - 1.5371385 * self.y - 0.4985314 * self.z
        g = -0.9692660 * self.x + 1.8760108 * self.y + 0.0415560 * self.z
        b = 0.0556434 * self.x - 0.2040259 * self.y + 1.0572252 * self.z

        return rgb(r, g, b)

    @classmethod
    @override
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        """https://www.oceanopticsbook.info/view/photometry-and-visibility/from-xyz-to-rgb"""
        # [X]   [0.4124564   0.3575761   0.1804375] [R]
        # [Y] = [0.2126729   0.7151522   0.0721750] [G]
        # [Z]   [0.0193339   0.1191920   0.9503041] [B]

        x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
        y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
        z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

        return cls(x, y, z)


@dataclass(frozen=True, slots=True)
class oklab(ColorSpace):
    """(L, a, b) Oklab color space designed for perceptual uniformity, color blending, etc.

    0 <= lightness <= 1  (black -> white)
    -0.5 <= a <= 0.5     (green -> red)
    -0.5 <= b <= 0.5     (blue -> yellow)
    """

    lightness: float
    a: float
    b: float

    @classmethod
    def _from_ciexyz(cls, x: float, y: float, z: float) -> Self:
        """https://en.wikipedia.org/wiki/Oklab_color_space#Conversion_from_CIE_XYZ"""

        # 1. Applying the linear map which converts the XYZ values into a space analogous to the LMS color space:
        #
        #   <l, m, s> = M1 @ <X, Y, Z>
        #
        # where
        #
        #      [0.8189330101      0.3618667424     -0.1288597137]
        # M1 = [0.0329845436      0.9293118715      0.0361456387]
        #      [0.0482003018      0.2643662691      0.6338517070]
        ell = 0.8189330101 * x + 0.3618667424 * y - 0.1288597137 * z
        m = 0.0329845436 * x + 0.9293118715 * y + 0.0361456387 * z
        s = 0.0482003018 * x + 0.2643662691 * y + 0.6338517070 * z

        # 2. Applying a cube root non-linearity:
        #
        #   <l', m', s'> = <l^(1/3), m^(1/3), s^(1/3)>
        ell_prime = pow(ell, 1 / 3)
        m_prime = pow(m, 1 / 3)
        s_prime = pow(s, 1 / 3)

        # 3. Converting to Oklab with another linear map:
        #
        #   <L, a, b> = M2 @ <l', m', s'>
        #
        # where
        #      [0.2104542553      0.7936177850     -0.0040720468]
        # M2 = [1.9779984951     -2.4285922050      0.4505937099]
        #      [0.0259040371      0.7827717662     -0.8086757660]
        L = 0.2104542553 * ell_prime + 0.7936177850 * m_prime - 0.0040720468 * s_prime
        a = 1.9779984951 * ell_prime - 2.4285922050 * m_prime + 0.4505937099 * s_prime
        b = 0.0259040371 * ell_prime + 0.7827717662 * m_prime - 0.8086757660 * s_prime

        return cls(L, a, b)

    @override
    def as_ciexyz(self) -> ciexyz:
        """https://en.wikipedia.org/wiki/Oklab_color_space#Conversion_to_CIE_XYZ_and_sRGB"""
        # "Converting to CIE XYZ and sRGB simply involves applying the respective inverse functions in reverse order:
        #
        # <l', m', s'> = inv(M2) @ <L, a, b>
        # Obviously, we'll precompute:
        #
        #           [1     0.396338      0.215804 ]
        # inv(M2) = [1    -0.105561     -0.0638542]
        #           [1    -0.0894842    -1.29149  ]
        ell_prime = 1 * self.lightness + 0.396338 * self.a + 0.215804 * self.b
        m_prime = 1 * self.lightness - 0.105561 * self.a - 0.0638542 * self.b
        s_prime = 1 * self.lightness - 0.0894842 * self.a - 1.29149 * self.b

        # <l, m, s> = <(l')^3, (m')^3, (s')^3>
        ell = pow(ell_prime, 3)
        m = pow(m_prime, 3)
        s = pow(s_prime, 3)

        # <X, Y, Z> = inv(M1) @ <l, m, s>
        #
        #           [ 1.22701          -0.5578       0.281256 ]
        # inv(M1) = [-0.0405802         1.11226     -0.0716767]
        #           [-0.0763813        -0.421482     1.58616  ]
        x = 1.22701 * ell - 0.5578 * m + 0.281256 * s
        y = -0.0405802 * ell + 1.11226 * m - 0.0716767 * s
        z = -0.0763813 * ell - 0.421482 * m + 1.58616 * s

        return ciexyz(x, y, z)

    @override
    def __rgb__(self) -> rgb:
        # It's easier to convert through CIE XYZ than it is to go directly.
        return self.as_ciexyz().__rgb__()

    @classmethod
    @override
    def __from_rgb__(cls, r: float, g: float, b: float) -> Self:
        # Again, it's easier to convert through CIE XYZ.
        return cls._from_ciexyz(*ciexyz.__from_rgb__(r, g, b))

    @property
    def L(self) -> float:
        return self.lightness


def _square_distance(x: ColorSpace, y: ColorSpace, /, *, perceptive: bool = False) -> float:
    """Return the square distance between the two colors. perceptive=False -> sRGB, perceptive=True -> Oklab."""
    if perceptive:
        # x, y, z ~ L, a, b
        x1, y1, z1 = x.as_oklab()
        x2, y2, z2 = y.as_oklab()
    else:
        # x, y, z ~ r, g, b
        x1, y1, z1 = x.as_rgb()
        x2, y2, z2 = y.as_rgb()

    return pow(x1 - x2, 2) + pow(y1 - y2, 2) + pow(z1 - z2, 2)


def distance(x: ColorSpace, y: ColorSpace, /, *, perceptive: bool = False) -> float:
    """Return the distance between the two colors. perceptive=False -> sRGB, perceptive=True -> Oklab."""
    return pow(_square_distance(x, y, perceptive=perceptive), 0.5)


def nearest(
    color: ColorSpace, palette: Iterable[ColorSpace], *, perceptive: bool = False
) -> ColorSpace:
    """Return the color in the palette which is closest to the given color.
    If perceptive=False, use sRGB distance; if perceptive=True, use Oklab distance.
    """
    palette = iter(palette)

    try:
        best = next(palette)
        best_distance = _square_distance(color, best, perceptive=perceptive)
    except StopIteration:
        raise ValueError("palette is empty")

    for candidate in palette:
        if (dist := _square_distance(color, candidate, perceptive=perceptive)) < best_distance:
            best = candidate
            best_distance = dist

    return best
