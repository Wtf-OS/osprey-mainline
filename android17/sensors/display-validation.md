# Osprey INX display verification

DSI commands retuned the 28nm PLL during video output. Removing the repeated
link-rate request in xfer_prepare leaves power-on clock programming intact.
Five isolated brightness updates produced zero DSI/MDSS set_rate events.
The user confirmed that slider changes and Power wake no longer flicker or
shift the image. Android completed boot and charging resumed. Long-term
stress testing has not been performed. HS brightness and continuous-clock
probes were reverted. The short passing check does not prove all panel issues
are resolved on every hardware variant.
