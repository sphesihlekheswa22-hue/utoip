"""UITOP package."""
from uitop import create_app

app = create_app()

if __name__ == "__main__":
    # 0.0.0.0 so agents on other PCs can reach this machine on the LAN
    app.run(host="0.0.0.0", port=5500, debug=True)
