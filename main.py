from src.fetcher import GameDataFetcher
from src.overlay import OverlayApp

def main():
    fetcher = GameDataFetcher()
    
    app = OverlayApp(fetcher)
    app.run()

if __name__ == "__main__":
    main()