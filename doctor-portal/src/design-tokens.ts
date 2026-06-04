/**
 * Typed design-token exports for the doctor portal.
 * All values derive from @kyros/design-tokens/tokens.json — no hex literals here.
 * Import this file for dynamic styles (chart colors, conditional className logic).
 * For static styles, use the Tailwind token classes (bg-forest, text-ink, etc.).
 */
import tokens from '@kyros/design-tokens';

export const colors = tokens.colors as {
  forest:     string;
  jade:       string;
  sage:       string;
  saffron:    string;
  terracotta: string;
  ivory:      string;
  peachMist:  string;
  white:      string;
  ink:        string;
  stone:      string;
  alert:      string;
};

export const typography = tokens.typography as {
  fontFamily: {
    display: string[];
    body:    string[];
    hindi:   string[];
  };
  fontSize: {
    caption: string;
    body:    string;
    bodyLg:  string;
    h3:      string;
    h2:      string;
    h1:      string;
    display: string;
  };
  lineHeight: {
    caption: string;
    body:    string;
  };
  fontWeight: {
    normal:   string;
    medium:   string;
    semibold: string;
  };
};

export const spacing = tokens.spacing as Record<string, string>;

export const borderRadius = tokens.borderRadius as {
  sm: string;
  md: string;
  lg: string;
};

export const motion = tokens.motion as {
  duration: {
    micro:      string;
    entrance:   string;
    transition: string;
    lineDraw:   string;
    pullQuote:  string;
    statCount:  string;
    photoFade:  string;
  };
  easing: {
    out:   string;
    inOut: string;
  };
};
