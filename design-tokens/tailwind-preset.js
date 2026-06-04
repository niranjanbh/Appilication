// @ts-check
const tokens = require('./tokens.json');

/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        forest:       tokens.colors.forest,
        jade:         tokens.colors.jade,
        sage:         tokens.colors.sage,
        saffron:      tokens.colors.saffron,
        terracotta:   tokens.colors.terracotta,
        ivory:        tokens.colors.ivory,
        'peach-mist': tokens.colors.peachMist,
        ink:          tokens.colors.ink,
        stone:        tokens.colors.stone,
        alert:        tokens.colors.alert,
      },
      fontFamily: {
        display: tokens.typography.fontFamily.display,
        body:    tokens.typography.fontFamily.body,
        hindi:   tokens.typography.fontFamily.hindi,
      },
      fontSize: {
        caption:   [tokens.typography.fontSize.caption,  { lineHeight: tokens.typography.lineHeight.caption }],
        body:      [tokens.typography.fontSize.body,     { lineHeight: tokens.typography.lineHeight.body }],
        'body-lg': [tokens.typography.fontSize.bodyLg,   { lineHeight: tokens.typography.lineHeight.body }],
        h3:        [tokens.typography.fontSize.h3,       { lineHeight: '1.3' }],
        h2:        [tokens.typography.fontSize.h2,       { lineHeight: '1.25' }],
        h1:        [tokens.typography.fontSize.h1,       { lineHeight: '1.15' }],
        display:   [tokens.typography.fontSize.display,  { lineHeight: '1.0' }],
      },
      fontWeight: {
        normal:   tokens.typography.fontWeight.normal,
        medium:   tokens.typography.fontWeight.medium,
        semibold: tokens.typography.fontWeight.semibold,
      },
      borderRadius: {
        card:   tokens.borderRadius.md,
        button: tokens.borderRadius.sm,
        input:  tokens.borderRadius.sm,
      },
      transitionDuration: {
        micro:      tokens.motion.duration.micro,
        entrance:   tokens.motion.duration.entrance,
        transition: tokens.motion.duration.transition,
      },
      transitionTimingFunction: {
        out:    tokens.motion.easing.out,
        'in-out': tokens.motion.easing.inOut,
      },
    },
  },
};
