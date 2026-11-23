import io
from matplotlib.figure import Figure


def make_graph_png(records, threshold, interval_s):
    n = len(records)
    # x-axis: minutes ago (0 = now)
    minutes_ago = [-(n - 1 - i) * interval_s / 60 for i in range(n)]

    fig = Figure(figsize=(6, 3), dpi=100)
    ax = fig.subplots()
    ax.plot(minutes_ago, records, marker="o", markersize=3, label="Temp")
    ax.axhline(threshold, color="red", linestyle="--", label=f"Threshold ({threshold}°F)")
    ax.set_xlabel("Minutes ago")
    ax.set_ylabel("Temperature (°F)")
    ax.set_title("Recent Temperature")
    ax.grid(True, alpha=0.3)
    ax.legend()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    return buf.getvalue()