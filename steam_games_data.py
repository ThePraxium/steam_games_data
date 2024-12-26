import subprocess
import sys
print(f"###################################################################")
print(f"installing dependencies...")
# List of required dependencies
required_dependencies = [
    "requests",
    "pandas",
    "beautifulsoup4"
]

# Function to check and install missing dependencies
def install_dependencies():
    for package in required_dependencies:
        try:
            __import__(package)
            print(f"{package} is already installed.")
        except ImportError:
            print(f"{package} is not installed. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install dependencies if necessary
install_dependencies()

import requests
import pandas as pd
import csv
import time
from bs4 import BeautifulSoup
print(f"###################################################################")
print(f"This script is going to parse your steam account and the steam store to find the game name, app_id, playtime_hours, price, release_date, developer, publisher, genres, achievements_gained, achievements_total, save it to a file called ""steam_games_data.csv"" from where the script was launched, and then spit out some interesting statistics.")

print(f"###################################################################")
print(f"Get your Steam API key here: https://steamcommunity.com/dev/apikey, use localhost when it asks for a domain name.")

print(f"###################################################################")
print(f"Get your Steam ID by going to your steam Account Details, it will be near the top and look like Steam ID: 76561198004707326")

API_KEY = input("Please enter your API_KEY: ")
print(f"You entered: {API_KEY}")
STEAM_ID = input("Please enter your STEAM_ID: ") 
print(f"You entered: {STEAM_ID}")
#API_KEY = ""
#STEAM_ID = ""
BASE_URL = "https://api.steampowered.com"

# Fetch owned games
def get_owned_games():
    url = f"{BASE_URL}/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": API_KEY,
        "steamid": STEAM_ID,
        "include_appinfo": True,
        "include_played_free_games": True,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get('response', {}).get('games', [])
    else:
        print(f"Error fetching owned games: {response.status_code}")
        return []

#fetch game details
def get_game_details(app_id, index, total):
    print(f"Processing game ID: {app_id}...")
    url = f"https://store.steampowered.com/app/{app_id}/"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"[{index}/{total}] Failed to fetch details for app ID {app_id}")
            return {
                "price": "Unknown",
                "release_date": "Unknown",
                "developer": "Unknown",
                "publisher": "Unknown",
                "genres": "Unknown",
            }
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Fetch price
        price = soup.find("div", class_="game_purchase_price")
        if not price:
            price = soup.find("div", class_="discount_final_price")
        price = price.text.strip() if price else "Free"
        print(f"Price: {price}")
        
        # Fetch release date
        release_date = soup.find("div", class_="date")
        release_date = release_date.text.strip() if release_date else "Unknown"
        print(f"Release Date: {release_date}")
        
        # Fetch developer
        developer = soup.find("div", id="developers_list")
        developer = developer.text.strip() if developer else "Unknown"
        print(f"Developer: {developer}")
        
        # Fetch publisher
        publisher = "Unknown"
        labels = soup.find_all("div", class_="details_block")
        for label in labels:
            if "Publisher" in label.text:
                publisher = label.text.split(":")[1].strip()
                break
        print(f"Publisher: {publisher}")

        # Fetch genres
        genre_list = soup.find_all("a", class_="app_tag")
        genres = ", ".join([genre.text.strip() for genre in genre_list]) if genre_list else "Unknown"
        print(f"Genres: {genres}")
        
        return {
            "price": price,
            "release_date": release_date,
            "developer": developer,
            "publisher": publisher,
            "genres": genres,
        }
    
    except Exception as e:
        print(f"[{index}/{total}] Error fetching details for app ID {app_id}: {e}")
        return {
            "price": "Unknown",
            "release_date": "Unknown",
            "developer": "Unknown",
            "publisher": "Unknown",
            "genres": "Unknown",
        }

# Fetch achievements
def get_achievements(app_id):
    url = f"{BASE_URL}/ISteamUserStats/GetPlayerAchievements/v1/"
    params = {"key": API_KEY, "steamid": STEAM_ID, "appid": app_id}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json().get('playerstats', {})
        if 'achievements' in data:
            achievements = data['achievements']
            achieved = sum(1 for a in achievements if a['achieved'] == 1)
            total = len(achievements)
            return achieved, total
    return 0, 0

# Main function to collect data
def collect_game_data():
    games = get_owned_games()
    total_games = len(games)  # Total number of games
    game_data = []

    for index, game in enumerate(games, start=1):  # Loop with progress counter
        print(f"[{index}/{total_games}] Processing {game['name']}...")
        app_id = game['appid']
        
        # Pass index and total to get_game_details
        details = get_game_details(app_id, index, total_games)
        achievements_gained, achievements_total = get_achievements(app_id)

        game_data.append({
            "name": game['name'],
            "app_id": app_id,
            "playtime_hours": game['playtime_forever'] / 60,
            "price": details["price"],
            "release_date": details["release_date"],
            "developer": details["developer"],
            "publisher": details["publisher"],
            "genres": details["genres"],
            "achievements_gained": achievements_gained,
            "achievements_total": achievements_total,
        })

        # Avoid hitting the API rate limit
       # time.sleep(1)

    return game_data

# Save data to CSV
def save_to_csv(game_data, filename="steam_games_data.csv"):
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=game_data[0].keys())
        writer.writeheader()
        writer.writerows(game_data)
    print(f"Data saved to {filename}")

def load_data(file_path):
    """Loads the data from a CSV file and preprocesses it."""
    data = pd.read_csv(file_path)
    # Replace various non-numeric price formats with 0
    data['price'] = pd.to_numeric(
        data['price'].replace({'\\$': '', 'Free': '0', '0 To Play': '0'}, regex=True),
        errors='coerce'
    )
    data['release_date'] = pd.to_datetime(data['release_date'], errors='coerce')
    return data

def game_with_most_playtime(data):
    """Finds the game with the most playtime and its total playtime."""
    max_playtime = data.loc[data['playtime_hours'].idxmax()]
    return max_playtime['name'], max_playtime['playtime_hours']

def total_money_spent(data):
    """Calculates the total amount of money spent on the library."""
    return data['price'].sum()

def game_with_most_achievements(data):
    """Finds the game with the highest percentage of achievements gained."""
    data['achievement_percentage'] = (data['achievements_gained'] / data['achievements_total']) * 100
    max_achievements = data.loc[data['achievement_percentage'].idxmax()]
    return (max_achievements['name'], 
            max_achievements['achievements_gained'], 
            max_achievements['achievements_total'], 
            max_achievements['achievement_percentage'])

def oldest_published_game(data):
    """Finds the oldest published game in the library."""
    oldest_game = data.loc[data['release_date'].idxmin()]
    return oldest_game['name'], oldest_game['release_date']

def total_playtime(data):
    """Calculates the total playtime across all games."""
    return data['playtime_hours'].sum()

def post_interesting_statistics():
    # Load the data
    file_path = 'steam_games_data.csv'
    data = load_data(file_path)

    # 1. Game with the most playtime
    most_played_game, most_played_hours = game_with_most_playtime(data)
    print(f"Game with the most playtime: {most_played_game} ({most_played_hours:.2f} hours)")

    # 2. Total money spent on library
    total_spent = total_money_spent(data)
    print(f"Total amount of money spent on library: ${total_spent:.2f}")

    # 3. Game with the most achievements
    most_achievements_game, achievements_gained, achievements_total, most_achievement_percentage = game_with_most_achievements(data)
    print(f"Game with the highest achievement percentage: {most_achievements_game} ({achievements_gained}/{achievements_total} achievements, {most_achievement_percentage:.2f}%)")

    # 4. Oldest published game
    oldest_game, oldest_game_date = oldest_published_game(data)
    print(f"Oldest published game: {oldest_game} (Published on {oldest_game_date.date()})")

    # 5. Total playtime across all games
    total_playtime_hours = total_playtime(data)
    print(f"Total playtime across all games: {total_playtime_hours:.2f} hours")

#define the main
def main():
    """Main function to run the script."""
    game_data = collect_game_data()
    if game_data:
        save_to_csv(game_data)
        post_interesting_statistics()

#Run it!
if __name__ == "__main__":
    main()