"""
Master list of MRT/LRT station names currently in operation (as of mid-2026),
sourced from Wikipedia's List of Singapore MRT/LRT stations. Deduplicated by
name since interchange stations appear on multiple lines but share one
physical location. Jurong Region Line and Cross Island Line are not yet
open and are excluded.
"""

MRT_STATIONS = sorted(set([
    # North-South Line
    "Admiralty", "Ang Mo Kio", "Bishan", "Braddell", "Bukit Batok", "Bukit Gombak",
    "Canberra", "Choa Chu Kang", "City Hall", "Dhoby Ghaut", "Jurong East", "Khatib",
    "Kranji", "Marsiling", "Marina Bay", "Marina South Pier", "Novena", "Orchard",
    "Raffles Place", "Sembawang", "Somerset", "Toa Payoh", "Woodlands", "Yew Tee",
    "Yio Chu Kang", "Yishun",
    # East-West Line
    "Aljunied", "Bedok", "Boon Lay", "Bugis", "Buona Vista", "Chinese Garden",
    "Clementi", "Commonwealth", "Dover", "Eunos", "Expo", "Gul Circle", "Joo Koon",
    "Kallang", "Kembangan", "Pasir Ris", "Paya Lebar", "Pioneer", "Queenstown",
    "Redhill", "Tanah Merah", "Tanjong Pagar", "Tiong Bahru", "Tuas Crescent",
    "Tuas Link", "Tuas West Road",
    # North East Line
    "Boon Keng", "Buangkok", "Chinatown", "Clarke Quay", "Farrer Park",
    "HarbourFront", "Hougang", "Kovan", "Little India", "Outram Park",
    "Potong Pasir", "Punggol", "Punggol Coast", "Serangoon", "Woodleigh",
    # Circle Line
    "Bartley", "Bras Basah", "Caldecott", "Dakota", "Esplanade", "Farrer Road",
    "Haw Par Villa", "Holland Village", "Kent Ridge", "Labrador Park",
    "Lorong Chuan", "MacPherson", "Marymount", "Mountbatten", "Nicoll Highway",
    "one-north", "Pasir Panjang", "Promenade", "Stadium", "Tai Seng",
    "Telok Blangah", "Bayfront",
    # Downtown Line
    "Beauty World", "Bedok North", "Bedok Reservoir", "Bencoolen", "Bendemeer",
    "Botanic Gardens", "Bukit Panjang", "Cashew", "Downtown", "Fort Canning",
    "Geylang Bahru", "Hume", "Jalan Besar", "Kaki Bukit", "King Albert Park",
    "Mattar", "Newton", "Rochor", "Stevens", "Sixth Avenue", "Tan Kah Kee",
    "Tampines", "Tampines East", "Tampines West", "Ubi", "Upper Changi",
    # Thomson-East Coast Line
    "Bayshore", "Bright Hill", "Changi Airport", "Gardens by the Bay",
    "Great World", "Havelock", "Katong Park", "Lentor", "Maxwell", "Mayflower",
    "Napier", "Orchard Boulevard", "Shenton Way", "Springleaf", "Tanjong Katong",
    "Tanjong Rhu", "Upper Thomson", "Woodlands North", "Woodlands South",
]))

# LRT-only stations (not also served by an MRT line) - geocoded with an
# "LRT STATION" query suffix instead of "MRT STATION".
LRT_ONLY_STATIONS = sorted(set([
    # Bukit Panjang LRT
    "South View", "Keat Hong", "Teck Whye", "Phoenix", "Petir", "Pending",
    "Bangkit", "Fajar", "Segar", "Jelapang", "Senja",
    # Sengkang LRT
    "Compassvale", "Rumbia", "Bakau", "Kangkar", "Ranggung", "Cheng Lim",
    "Farmway", "Kupang", "Thanggam", "Fernvale", "Layar", "Tongkang", "Renjong",
    # Punggol LRT
    "Cove", "Meridian", "Coral Edge", "Riviera", "Kadaloor", "Oasis", "Damai",
    "Sam Kee", "Teck Lee", "Punggol Point", "Samudera", "Nibong", "Sumang",
    "Soo Teck",
]))
