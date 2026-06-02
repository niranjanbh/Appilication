// @ts-check
const tokens = require('./tokens.json');

/** @type {import('tailwindcss').Config} */
module.exports = {
  theme: {
    extend: {
      colors: {
        forest:     tokens.colors.forest,
        jade:       tokens.colors.jade,
        sage:       tokens.colors.sage,
        saffron:    tokens.colors.saffron,
        terracotta: tokens.colors.terracotta,
        ivory:      tokens.colors.ivory,
        'peach-mist': tokens.colors.peachMist,
        ink:        tokens.colors.ink,
        stone:      tokens.colors.stone,
        alert:      tokens.colors.alert,
      },
      fontFamily: {
        display: tokens.typography.fontFamily.display,
        body:    tokens.typography.fontFamily.body,
        hindi:   tokens.typography.fontFamily.hindi,
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
    },
  },
};
