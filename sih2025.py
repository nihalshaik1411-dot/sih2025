import streamlit as st
import time
import plotly.graph_objects as go

st.set_page_config(page_title="Gravity Battery - Seesaw Simulation", layout="wide")

# ---------- CONFIG ----------
FRAME_DELAY = 0.08   # seconds per animation frame (lower = faster)
GRAVITY = 9.81      # m/s²
HEIGHT = 100        # m (from +50m to -50m)
B1_CAPACITY = 100_000  # Joules (100 kJ for Battery 1)
B2_CAPACITY = 1_000_000  # Joules (1 MJ for Battery 2)
STORAGE_THRESHOLD = 80  # kg to trigger big cycle
MAX_TOTAL_BLOCKS = 20  # Max blocks (200kg) at A and B combined

# ---------- SESSION STATE ----------
if "blocks_top_A" not in st.session_state:
    st.session_state.blocks_top_A = 1  # initial 10 kg = 1 block
if "blocks_top_B" not in st.session_state:
    st.session_state.blocks_top_B = 2  # initial 20 kg = 2 blocks
if "tied_bottom_C" not in st.session_state:
    st.session_state.tied_bottom_C = 0
if "tied_bottom_D" not in st.session_state:
    st.session_state.tied_bottom_D = 0
if "storage_left" not in st.session_state:
    st.session_state.storage_left = 0
if "storage_right" not in st.session_state:
    st.session_state.storage_right = 0
if "battery1" not in st.session_state:
    st.session_state.battery1 = 0  # small battery % (0-100)
if "battery2" not in st.session_state:
    st.session_state.battery2 = 0  # big battery % (0-100)
if "generator_angle" not in st.session_state:
    st.session_state.generator_angle = 0
if "houses_lit" not in st.session_state:
    st.session_state.houses_lit = False
if "running" not in st.session_state:
    st.session_state.running = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False
if "logs" not in st.session_state:
    st.session_state.logs = []
if "step_count" not in st.session_state:
    st.session_state.step_count = 0

# ---------- DRAW / ANIMATION HELPERS ----------
def draw_scene(moving=None, move_y=None, moving_size=10, move_label="Dropping", note=""):
    """
    moving: None or tuple(point_name e.g. 'left'/'right'/'BIG', color)
    move_y: y coordinate of top of the moving rectangle
    moving_size: kg size for annotation (20 or 160)
    move_label: "Dropping" or "Lifting"
    """
    fig = go.Figure()
    # Ground line
    fig.add_shape(type="line", x0=-3, y0=0, x1=3, y1=0, line=dict(color="black", width=3))
    # Labels for points
    fig.add_annotation(x=-1.8, y=55, text="A (+50m)", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=1.8, y=55, text="B (+50m)", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=-1.8, y=-55, text="C (−50m)", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=1.8, y=-55, text="D (−50m)", showarrow=False, font=dict(size=12))

    # Draw stacked blocks at top A (left, blue)
    for i in range(st.session_state.blocks_top_A):
        y0 = 50 + i * 2.7
        fig.add_shape(type="rect", x0=-2.1, x1=-1.5, y0=y0, y1=y0 + 2.5, fillcolor="#2b6cb0", line=dict(color="black"))
    # Draw stacked blocks at top B (right, red)
    for i in range(st.session_state.blocks_top_B):
        y0 = 50 + i * 2.7
        fig.add_shape(type="rect", x0=1.5, x1=2.1, y0=y0, y1=y0 + 2.5, fillcolor="#c53030", line=dict(color="black"))

    # Tied block at bottom C (left, gray if present)
    if st.session_state.tied_bottom_C > 0:
        fig.add_shape(type="rect", x0=-2.1, x1=-1.5, y0=-51, y1=-48.5, fillcolor="gray", line=dict(color="black"))
    # Tied block at bottom D (right, gray if present)
    if st.session_state.tied_bottom_D > 0:
        fig.add_shape(type="rect", x0=1.5, x1=2.1, y0=-51, y1=-48.5, fillcolor="gray", line=dict(color="black"))

    # Stored blocks at left (below tied, orange)
    num_stored_left = st.session_state.storage_left // 10
    base_y_left = -51.05
    for i in range(num_stored_left):
        y1 = base_y_left - i * 2.7
        y0 = y1 - 2.5
        fig.add_shape(type="rect", x0=-2.1, x1=-1.5, y0=y0, y1=y1, fillcolor="#dd6b20", line=dict(color="black"))
    # Stored blocks at right (below tied, orange)
    num_stored_right = st.session_state.storage_right // 10
    base_y_right = -51.05
    for i in range(num_stored_right):
        y1 = base_y_right - i * 2.7
        y0 = y1 - 2.5
        fig.add_shape(type="rect", x0=1.5, x1=2.1, y0=y0, y1=y1, fillcolor="#dd6b20", line=dict(color="black"))

    # Optional moving block
    if moving and move_y is not None:
        pt, color = moving
        if pt == "left":
            x0, x1 = -2.1, -1.5
        elif pt == "right":
            x0, x1 = 1.5, 2.1
        elif pt == "BIG":
            x0, x1 = -1.2, 1.2
        else:
            x0, x1 = -0.6, 0.6
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=move_y, y1=move_y + 2.5, fillcolor=color, line=dict(color="black"))
        fig.add_annotation(x=0, y=move_y + 2.7, text=f"{move_label}: {moving_size}kg", showarrow=False)

    # Generator visual and angle
    angle = st.session_state.generator_angle % 360
    fig.add_shape(type="circle", x0=-0.4, y0=-20.6, x1=0.4, y1=-21.6, line=dict(color="orange", width=3))
    fig.add_annotation(x=0, y=-21.1, text=f"⚙ {angle:.0f}°", showarrow=False, font=dict(color="orange"))

    # Battery labels
    fig.add_annotation(x=-2.7, y=45, text=f"🔋 B1: {st.session_state.battery1:.0f}%", showarrow=False)
    fig.add_annotation(x=2.7, y=45, text=f"🔋 B2: {st.session_state.battery2:.0f}%", showarrow=False)

    # Houses indicator
    houses_text = "🏠 lit" if st.session_state.houses_lit else "dark"
    fig.add_annotation(x=0, y=45, text=houses_text, showarrow=False)

    fig.update_xaxes(visible=False, range=[-4, 4])
    fig.update_yaxes(visible=False, range=[-65, 65])
    fig.update_layout(height=600, margin=dict(l=10, r=10, t=10, b=10), autosize=True)
    return fig

def animate_move(placeholder, pt, color="#2b6cb0", start_y=50, end_y=-50, steps=50, size_kg=20):
    label = "Lifting" if end_y > start_y else "Dropping"
    for step in range(steps):
        if st.session_state.stop_requested:
            return False
        t = step / (steps - 1)
        y = start_y + (end_y - start_y) * t
        fig = draw_scene(moving=(pt, color), move_y=y, moving_size=size_kg, move_label=label)
        placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(FRAME_DELAY)
    return True

# ---------- MAIN UI ----------
st.title("⚡ Gravity Battery — Seesaw Continuous Simulation")

left_col, mid_col, right_col = st.columns([1, 2, 1])

with left_col:
    st.subheader("Controls")
    if st.button("Start"):
        st.session_state.running = True
        st.session_state.stop_requested = False
        st.session_state.logs = []
        st.session_state.step_count = 0
    if st.button("Stop"):
        st.session_state.stop_requested = True
        st.session_state.running = False

    st.write("Initial top stacks (editable, max 200kg total):")
    blocks_a = st.number_input("Blocks at top A (10kg each)", min_value=0, max_value=MAX_TOTAL_BLOCKS, value=st.session_state.blocks_top_A, step=1)
    blocks_b = st.number_input("Blocks at top B (10kg each)", min_value=0, max_value=MAX_TOTAL_BLOCKS, value=st.session_state.blocks_top_B, step=1)
    if blocks_a + blocks_b <= MAX_TOTAL_BLOCKS:
        st.session_state.blocks_top_A = blocks_a
        st.session_state.blocks_top_B = blocks_b
    else:
        st.error(f"Total blocks (A + B) must not exceed {MAX_TOTAL_BLOCKS} (200kg).")

with mid_col:
    scene_ph = st.empty()

with right_col:
    st.subheader("Status")
    total_storage = st.session_state.storage_left + st.session_state.storage_right
    total_mass = (st.session_state.blocks_top_A + st.session_state.blocks_top_B +
                  st.session_state.tied_bottom_C + st.session_state.tied_bottom_D +
                  st.session_state.storage_left // 10 + st.session_state.storage_right // 10) * 10
    st.write(f"Step: {st.session_state.step_count}")
    st.write(f"Top A: {st.session_state.blocks_top_A * 10} kg")
    st.write(f"Top B: {st.session_state.blocks_top_B * 10} kg")
    st.write(f"Tied at C: {st.session_state.tied_bottom_C * 10} kg")
    st.write(f"Tied at D: {st.session_state.tied_bottom_D * 10} kg")
    st.write(f"Storage left (C): {st.session_state.storage_left} kg")
    st.write(f"Storage right (D): {st.session_state.storage_right} kg")
    st.write(f"Total storage: {total_storage} kg")
    st.write(f"Total mass: {total_mass} kg")
    st.write(f"Battery B1: {st.session_state.battery1:.0f}%")
    st.write(f"Battery B2: {st.session_state.battery2:.0f}%")
    st.write(f"Generator angle: {st.session_state.generator_angle:.0f}°")
    if st.session_state.houses_lit:
        st.success("Houses are lit by B1!")
    else:
        st.info("Houses are not lit yet")

# Render scene
scene_ph.plotly_chart(draw_scene(), use_container_width=True)

# ---------- SIMULATION STEP ----------
if st.session_state.running and not st.session_state.stop_requested:
    dropped = False
    side = None
    opposite = None
    color = None
    lifted = 0

    # Log state
    total_storage = st.session_state.storage_left + st.session_state.storage_right
    st.session_state.step_count += 1
    state_log = (
        f"--- Step {st.session_state.step_count - 1} ---\n"
        f"Top A: {st.session_state.blocks_top_A * 10}kg | Top B: {st.session_state.blocks_top_B * 10}kg\n"
        f"Tied C: {st.session_state.tied_bottom_C * 10}kg | Tied D: {st.session_state.tied_bottom_D * 10}kg\n"
        f"Storage L: {st.session_state.storage_left}kg | Storage R: {st.session_state.storage_right}kg | Total: {total_storage}kg\n"
        f"B1: {st.session_state.battery1}% | B2: {st.session_state.battery2}% | Gen: {st.session_state.generator_angle}°\n"
        f"Houses: {'lit' if st.session_state.houses_lit else 'dark'}"
    )
    st.session_state.logs.append(state_log)
    st.session_state.logs = st.session_state.logs[-100:]  # Limit to last 100 entries

    left_color = "#2b6cb0"
    right_color = "#c53030"

    # Check for drops
    if st.session_state.blocks_top_A == 2 and st.session_state.blocks_top_B < 2:
        ok = animate_move(scene_ph, "left", left_color, start_y=50, end_y=-50, steps=50)
        if not ok:
            st.session_state.stop_requested = True
        st.session_state.blocks_top_A = 0
        st.session_state.storage_left += 10
        st.session_state.tied_bottom_C += 1
        lifted = st.session_state.tied_bottom_D
        if lifted > 0:
            st.session_state.tied_bottom_D = 0
            ok = animate_move(scene_ph, "right", right_color, start_y=-50, end_y=50, steps=50)
            if not ok:
                st.session_state.stop_requested = True
            st.session_state.blocks_top_B += lifted
        side, opposite, color = "left", "right", left_color
        dropped = True
    elif st.session_state.blocks_top_B == 2 and st.session_state.blocks_top_A < 2:
        ok = animate_move(scene_ph, "right", right_color, start_y=50, end_y=-50, steps=50)
        if not ok:
            st.session_state.stop_requested = True
        st.session_state.blocks_top_B = 0
        st.session_state.storage_right += 10
        st.session_state.tied_bottom_D += 1
        lifted = st.session_state.tied_bottom_C
        if lifted > 0:
            st.session_state.tied_bottom_C = 0
            ok = animate_move(scene_ph, "left", left_color, start_y=-50, end_y=50, steps=50)
            if not ok:
                st.session_state.stop_requested = True
            st.session_state.blocks_top_A += lifted
        side, opposite, color = "right", "left", right_color
        dropped = True
    elif st.session_state.blocks_top_A == 2 and st.session_state.blocks_top_B == 2:
        # Alternate drops when both sides have 2 blocks
        if st.session_state.step_count % 2 == 0:
            ok = animate_move(scene_ph, "left", left_color, start_y=50, end_y=-50, steps=50)
            if not ok:
                st.session_state.stop_requested = True
            st.session_state.blocks_top_A = 0
            st.session_state.storage_left += 10
            st.session_state.tied_bottom_C += 1
            lifted = st.session_state.tied_bottom_D
            if lifted > 0:
                st.session_state.tied_bottom_D = 0
                ok = animate_move(scene_ph, "right", right_color, start_y=-50, end_y=50, steps=50)
                if not ok:
                    st.session_state.stop_requested = True
                st.session_state.blocks_top_B += lifted
            side, opposite, color = "left", "right", left_color
        else:
            ok = animate_move(scene_ph, "right", right_color, start_y=50, end_y=-50, steps=50)
            if not ok:
                st.session_state.stop_requested = True
            st.session_state.blocks_top_B = 0
            st.session_state.storage_right += 10
            st.session_state.tied_bottom_D += 1
            lifted = st.session_state.tied_bottom_C
            if lifted > 0:
                st.session_state.tied_bottom_C = 0
                ok = animate_move(scene_ph, "left", left_color, start_y=-50, end_y=50, steps=50)
                if not ok:
                    st.session_state.stop_requested = True
                st.session_state.blocks_top_A += lifted
            side, opposite, color = "right", "left", right_color
        dropped = True

    if not dropped:
        time.sleep(0.2)
        st.rerun()
        # If no drop, short sleep and rerun to check again

    # Generate power for small drop (20kg)
    energy_joules = 20 * GRAVITY * HEIGHT  # 19,620 J
    st.session_state.battery1 = min(st.session_state.battery1 + (energy_joules / B1_CAPACITY) * 100, 100)
    st.session_state.generator_angle += (energy_joules / B1_CAPACITY) * 360  # Proportional rotation
    st.session_state.houses_lit = st.session_state.battery1 >= 10

    # Log drop event
    lift_to = "B" if opposite == "right" else "A"
    drop_to = "C" if side == "left" else "D"
    st.session_state.logs.append(
        f"Action: Dropped 20kg from {side.upper()} to {drop_to}, stored 10kg, tied 10kg. "
        f"Lifted {lifted * 10}kg to {lift_to}. B1 +{(energy_joules / B1_CAPACITY) * 100:.1f}%, Generator +{(energy_joules / B1_CAPACITY) * 360:.0f}°."
    )
    # Add 10kg to opposite side
    if opposite == "left":
        st.session_state.blocks_top_A += 1
        add_side = "A"
    else:
        st.session_state.blocks_top_B += 1
        add_side = "B"
    st.session_state.logs.append(f"Action: Added 10kg to {add_side}.")
    st.session_state.logs = st.session_state.logs[-100:]

    # Update scene after drop
    scene_ph.plotly_chart(draw_scene(), use_container_width=True)
    time.sleep(0.4)

    # Check for STORAGE threshold -> trigger BIG CYCLE
    total_storage = st.session_state.storage_left + st.session_state.storage_right
    if total_storage >= STORAGE_THRESHOLD:
        st.session_state.logs.append(f"Action: Big cycle triggered (Storage = {total_storage}kg). Dropping 160kg...")
        ok = animate_move(scene_ph, "BIG", "#805ad5", start_y=50, end_y=-50, steps=60, size_kg=160)
        if not ok:
            st.session_state.stop_requested = True
        energy_joules = 160 * GRAVITY * HEIGHT  # 156,960 J
        st.session_state.generator_angle += (energy_joules / B2_CAPACITY) * 360
        st.session_state.battery2 = min(st.session_state.battery2 + (energy_joules / B2_CAPACITY) * 100, 100)
        st.session_state.storage_left = 0
        st.session_state.storage_right = 0
        st.session_state.battery2 = max(st.session_state.battery2 - (80_000 / B2_CAPACITY) * 100, 0)  # Assume 80 kJ to lift
        total_storage = st.session_state.storage_left + st.session_state.storage_right
        st.session_state.logs.append(
            f"--- Step {st.session_state.step_count} ---\n"
            f"Top A: {st.session_state.blocks_top_A * 10}kg | Top B: {st.session_state.blocks_top_B * 10}kg\n"
            f"Tied C: {st.session_state.tied_bottom_C * 10}kg | Tied D: {st.session_state.tied_bottom_D * 10}kg\n"
            f"Storage L: {st.session_state.storage_left}kg | Storage R: {st.session_state.storage_right}kg | Total: {total_storage}kg\n"
            f"B1: {st.session_state.battery1}% | B2: {st.session_state.battery2}% | Gen: {st.session_state.generator_angle}°\n"
            f"Houses: {'lit' if st.session_state.houses_lit else 'dark'}\n"
            f"Action: Big cycle: Dropped 160kg, B2 +{(energy_joules / B2_CAPACITY) * 100:.1f}%, "
            f"Gen +{(energy_joules / B2_CAPACITY) * 360:.0f}°. Reset storages. Used {(80_000 / B2_CAPACITY) * 100:.1f}% B2 to lift 160kg."
        )
        st.session_state.logs = st.session_state.logs[-100:]
        st.session_state.houses_lit = st.session_state.battery1 >= 10
        scene_ph.plotly_chart(draw_scene(), use_container_width=True)
        time.sleep(0.6)

    # Rerun to update UI with new values
    st.rerun()

# Event Log display
st.subheader("Simulation Steps & Events")
st.text_area("Simulation Log", value="\n".join(st.session_state.logs), height=300, disabled=True)
