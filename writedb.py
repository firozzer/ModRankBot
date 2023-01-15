import sqlite3

def recordVoteInDB(modName: str, positiveVote: bool, subreddits: str):
    con = sqlite3.connect("modrank.db")
    cursor = con.cursor()
    # cursor.execute("CREATE TABLE mods(username TEXT UNIQUE, pos_votes INTEGER, neg_votes INTEGER, subreddits TEXT)")
    # cursor.execute("DELETE from mods") # delete all recoreds

    if positiveVote:
        cursor.execute("""
        INSERT INTO mods VALUES (?, 1, 0, ?) 
        ON CONFLICT(username) DO UPDATE SET pos_votes=pos_votes+1, subreddits=?
        """, (modName, subreddits, subreddits)) # use this ? syntax to avoid sql injection
    else:
        cursor.execute("""
        INSERT INTO mods VALUES (?, 0, 1, ?) 
        ON CONFLICT(username) DO UPDATE SET neg_votes=neg_votes+1, subreddits=?
        """, (modName, subreddits, subreddits))

    con.commit()
    # print(cursor.execute("SELECT * FROM mods").fetchall())
    con.close()
