"""Export a slower, root-to-tip swimming wave using short articulated joints."""
import json
import math
import os
import sys

DURATION = 6.0
STEP = .125
JOINTS = {"outer": 8, "inner": 6}

def rotation(kind, index, joint, time):
    count = JOINTS[kind]
    u = (joint + .5) / count
    theta = math.tau * index / 8 + (math.pi/8 if kind == "inner" else 0)
    phase = index*.79 + (.55 if kind == "inner" else 0)
    cycle = math.tau * time / DURATION
    # The phase decreases toward the tip, so crests travel away from the bell.
    wave = cycle + phase - u*(2.1 if kind == "outer" else 2.5)
    amplitude = (.85 + 3.45*u**1.6) if kind == "outer" else (1.15 + 4.45*u**1.7)
    primary = amplitude*(math.sin(wave) + .14*math.sin(2*wave+.45))/1.14
    secondary = amplitude*.68*math.cos(wave-.40)
    twist = amplitude*.16*math.sin(cycle+phase-u*1.6)
    return [round(v,4) for v in (
        primary*math.cos(theta) + secondary*math.sin(theta),
        twist,
        primary*math.sin(theta) - secondary*math.cos(theta),
    )]

def payload():
    times = [i*STEP for i in range(round(DURATION/STEP)+1)]
    bones = {}
    for kind,count in JOINTS.items():
        for index in range(8):
            for joint in range(count):
                name = f"tentacle_{kind}_{index+1:02d}_{joint+1:02d}"
                keys = {f"{t:.3f}":rotation(kind,index,joint,t) for t in times}
                keys[f"{DURATION:.3f}"] = keys["0.000"].copy()
                bones[name] = {"rotation":keys}
    # Keep the established four-second pulse in its own animation so both
    # animation loops close without imposing the tentacle period on the bell.
    bell_keys = {
        f"{i*STEP:.3f}":[round(1+.025*math.sin(math.tau*i*STEP/4),6),
                       round(1-.018*math.sin(math.tau*i*STEP/4),6),
                       round(1+.025*math.sin(math.tau*i*STEP/4),6)]
        for i in range(round(4/STEP)+1)}
    bell_keys["4.000"] = bell_keys["0.000"].copy()
    return {"format_version":"1.8.0","animations":{
        "animation.pinene.jellyfish_boss.idle":{
            "loop":True,"animation_length":DURATION,"bones":bones},
        "animation.pinene.jellyfish_boss.pulse":{
            "loop":True,"animation_length":4.0,"bones":{"bell":{"scale":bell_keys}}},
        "animation.pinene.jellyfish_boss.distant":{
            "loop":True,"animation_length":4.0,"bones":{"bell":{"scale":bell_keys}}},
    }}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python export_flexible_animation.py OUTPUT.animation.json")
    out = os.path.abspath(sys.argv[1])
    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,"w",encoding="utf-8") as handle:
        json.dump(payload(),handle,ensure_ascii=False,indent=2)
        handle.write("\n")
    print("FLEXIBLE_ANIMATION", "tentacle_channels=112", "pulse_channels=1",
          "period_seconds=6", "key_interval_seconds=.125")
