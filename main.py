#!/home/ubuntu/modrankbot/venv/bin/python3

import logging, sys, os, requests, json

import praw

from writedb import recordVoteInDB
from generateHTML import generateHTMLAndPushToGithub
from myCreds import *

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def sendTgMessage(message):
    url = f'https://api.telegram.org/bot{tgBotToken}/sendMessage' # ripl shipping spam bot this is 
    payload = {'chat_id':myTgID, 'text': f"""{message}"""}
    requests.post(url,json=payload)

def checkIfParentReallyIsModOfTHATSub(commentObj, parentAuthorObj, author):
    """
    Returns str of subs modded by parent, if indeed parent was mod of that sub.
    Else, returns False. Also returns False if parent was AutoMod
    """
    if parentAuthorObj.name == "AutoModerator" or parentAuthorObj.name == author:
        return False
    subWhereCommentWasMade = commentObj.subreddit
    subsModdedByParent = parentAuthorObj.moderated()
    if subWhereCommentWasMade in subsModdedByParent:
        subsModdedByParent = [subName.display_name for subName in subsModdedByParent]
        return ' '.join(subsModdedByParent)
    return False

def checkTheComment(subreddit:str, respData: dict, adj:str, diskData:dict, positiveVote:bool):
    commentsPrvslyCheckedStr = diskData['commentsPrvslyChecked'] # saving these as pushshift will naturally send dupes every min of checking
    postsWhereiAlreadyCommentedStr = diskData['postsWhereiAlreadyCommented'] # saving these so as not to post > once in a post, DM instead
    OPTED_OUT_USERS_LIST = diskData['optedOutUsers'] # not automated opted out user collection yet, add manualy into JSON whenever someone tells
    SKIP_THESE_SUBS_LIST = diskData['skipTheseSubs'] # reloading this just to avoid scope probs on older pythons
    
    author = respData['author'].lower()
    if author[:2] == 'u/': author = author[2:] # who knows if Pushshift will give prepended or not, so this check in place
    comment = respData['body']
    commentID = respData['id']
    commentTBCompared = comment.lower().strip(" .!,")
    if commentTBCompared == f'{adj} mod' or commentTBCompared == f'the {adj} mod':
        # check if comment was prevsly handled, as pushshift will naturally send dupes. If it was prevsly handled, just return.
        if commentID in commentsPrvslyCheckedStr:
            return

        # if reached this stage means a new vote has been detected
        commentObj = REDDIT_OBJ.comment(commentID)
        parentCommentObj = commentObj.parent()
        commentURL = f"https://www.reddit.com/{respData['permalink']}"
        myLogger.info(f"{author}\n{comment}\n{subreddit}\n{commentURL}\n{parentCommentObj.author} is parent")
        parentAuthorObj = parentCommentObj.author
        parentName = parentAuthorObj.name # not doing lower as hoping Reddit API will maintain proper capitalization lifelong.
        if parentName[:2] == 'u/': parentName = parentName[2:] # who knows if Reddit API will give prepended or not, so this check in place
        
        subsModdedByParent = checkIfParentReallyIsModOfTHATSub(commentObj, parentAuthorObj, author)
        if subsModdedByParent:
            myLogger.info("recording db")
            recordVoteInDB(parentName, positiveVote, subsModdedByParent, subreddit)

            userHasOptedOutOfReceivingReplies = [x for x in OPTED_OUT_USERS_LIST if x.lower() == author.lower()]
            if userHasOptedOutOfReceivingReplies:
                myLogger.info(f"Not replying or DMing u{author} as they are in opt out list.")
            else:
                # Comment or DM commenter vote confirmation. If prevsly commented in post then DM instead (spam reduction).
                postID = respData['link_id'][3:]
                if postID not in postsWhereiAlreadyCommentedStr:
                    try:
                        commentObj.reply(f"Thanks for voting on **{parentName}**. Reply '!OptOut' to stop replying.\n\n*Check out the [rankings table](https://modrank.netlify.app/).*")
                        myLogger.info(f"Commented succyly: {commentURL}")
                        # sendTgMessage(f"Mod Rank Bot commented: {commentURL}")
                        # record post ID where commented, so as not to coment again in that post to reduce spam
                        postsWhereiAlreadyCommentedStr += f" {postID}"
                    except Exception as e: # if public comment fails for some reason, DM
                        myLogger.info(f"ModRankBot Couldn't comment publicly. Commenter: {author} , ParentMod: {parentName}, Sub: {subreddit}. Is this a banned sub? See if error is specific to banned sub. Anyway, sending DM to {author}. Error is: {e}. DM'ing u/{author}")
                        sendTgMessage(f"ModRankBot Couldn't comment publicly. Commenter: {author} , ParentMod: {parentName}, Sub: {subreddit}. Is this a banned sub? See if error is specific to banned sub. Anyway, sending DM to {author}. Error is: {e}. DM'ing u/{author}")
                        try:
                            commentAuthorObj = REDDIT_OBJ.redditor(author)
                            commentAuthorObj.message(subject=f"Thanks for voting on u/{parentName} in r/{subreddit}", message=f"[Your vote]({commentURL}) has been successfully recorded. Reply '!OptOut' to stop replying.\n\n*Check out the [rankings table](https://modrank.netlify.app/).*")
                        except Exception as e:
                            myLogger.error(f"Error when trying to DM {author} https://reddit.com/{postID} : {e}")
                            sendTgMessage(f"ModRank Bot failed to DM https://reddit.com/{postID}, DM failed to u/{author}.")
                else:
                    myLogger.info(f"Already commented in Post {postID}, so DMing u/{author}.")
                    try:
                        commentAuthorObj = REDDIT_OBJ.redditor(author)
                        commentAuthorObj.message(subject=f"Thanks for voting on u/{parentName} in r/{subreddit}", message=f"[Your vote]({commentURL}) has been successfully recorded. Reply '!OptOut' to stop replying.\n\n*Check out the [rankings table](https://modrank.netlify.app/).*")
                        myLogger.info(f"ModRank Bot already commented in Post https://reddit.com/{postID}, so DM'd u/{author}.")
                        # sendTgMessage(f"ModRank Bot already commented in Post https://reddit.com/{postID}, so DM'd u/{author}.")
                    except Exception as e:
                        myLogger.error(f"Error when trying to DM {author} https://reddit.com/{postID} : {e}")
                        sendTgMessage(f"ModRank Bot failed to DM https://reddit.com/{postID}, DM failed to u/{author}.")
        else:
            if author == parentAuthorObj.name:
                myLogger.info(f"False self vote by mod")
            elif parentCommentObj.author == 'AutoModerator':
                myLogger.info(f"Skipped recording vote since parent was AutoMod.")
            else:
                myLogger.warning(f"False comment. {parentName} isn't a mod of {subreddit}, where comment was made.")
        
        # record json to disk
        commentsPrvslyCheckedStr += f" {commentID}"
        newDiskData = {}
        newDiskData['skipTheseSubs'] = SKIP_THESE_SUBS_LIST
        newDiskData['optedOutUsers'] = OPTED_OUT_USERS_LIST
        
        noOfIDsIWishToMaintainInJSON = 200 # pushshift will give 100 unique IDs MAX in 1 go, so 200 is > safe.
        # trimming prevsly checked comment IDs. Decided not to trim post IDs where i commented coz may happen that months later someone might post 'good mod' in an old post where i already commented, & i'll spam again having no record of that
        commentsPrvslyCheckedList = commentsPrvslyCheckedStr.split()
        noOfOldIDsTBTrimmed = len(commentsPrvslyCheckedList) - noOfIDsIWishToMaintainInJSON
        commentsPrvslyCheckedList = commentsPrvslyCheckedList[noOfOldIDsTBTrimmed:] # trimming from front as newer IDs are appended to str at end
        commentsPrvslyCheckedStr = ' '.join(commentsPrvslyCheckedList)
        newDiskData['commentsPrvslyChecked'] = commentsPrvslyCheckedStr
        
        newDiskData['postsWhereiAlreadyCommented'] = postsWhereiAlreadyCommentedStr
        with open('diskData.json', 'w', encoding='utf8') as f:
            json.dump(newDiskData, f)

        return parentName

# configure logging settings
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    myLogger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception # this helps to log all uncaught exceptions
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s-%(levelname)s- %(message)s',
                    handlers=[logging.FileHandler(f"log{os.path.basename(__file__)[:-3]}.txt"), logging.StreamHandler()])
myLogger = logging.getLogger('myLogger')
myLogger.setLevel(logging.DEBUG)

with open('diskData.json', encoding='utf8') as f:
  diskData = json.load(f)

SKIP_THESE_SUBS_LIST = diskData['skipTheseSubs']

idxOfModRankBotCreds = rdtUsrnms.index('modrankbot')
REDDIT_OBJ = praw.Reddit(client_id=rdtClntIDs[idxOfModRankBotCreds],client_secret=rdtClntSecs[idxOfModRankBotCreds],user_agent=rdtUsrnms[idxOfModRankBotCreds], username=rdtUsrnms[idxOfModRankBotCreds],password=rdtPswds[idxOfModRankBotCreds])

GOOD_ADJS = ['good', 'great', 'greatest', 'best', 'awesome', 'amazing', 'nice', 'excellent', 'superb', "excellente", "excelent", "wonderful", "brave", "super", "incredible", "sweet", "lovely", "bold", "sexy", "gg", 'cool', 'mvp', 'og', 'goat', 'chad', 'legendary', 'based', 'dope', 'gigachad', 'goated', 'danke', 'dank']
BAD_ADJS = ['bad', 'worst', "insensitive", "harsh", "rash", "rude", "senseless", "dictatorial", 'dumb', 'inconsiderate', 'shitty', 'stupid', 'foolish']

# preparing URL to ping on Pushshift. If term is phrase then wrap in quotes. OR can be indicated with Pipe symbol
thenewAdjs = [f'"{x}' for x in set(GOOD_ADJS+BAD_ADJS)] # set is to remove dupes if any
searchTerm = '%20mod"|'.join(thenewAdjs)+'%20mod"'
finalURL = f"https://api.pushshift.io/reddit/search/comment/?q={searchTerm}&limit=100"

try:
    r = requests.get(finalURL, timeout=60) # timeout is in secs
except Exception as e:
    myLogger.error(f"Quitting. Pushshift API gave error: {e}")
    quit()

if r.ok:
    respJson = r.json()
else:
    myLogger.error(f"Received 'not ok' resp from Pushshift. Status code: {r.status_code}, Content: {r.content}")
    quit()

websiteToBeUpdatedForNewVotesOnTheseMods = []

for respData in respJson['data']:            
    subreddit = respData['subreddit_name_prefixed'].lower()
    if subreddit[:2] == 'r/': subreddit = subreddit[2:] # who knows if Pushshift will give prepended or not, so this check in place
    
    aSubToBeSkipped = [x for x in SKIP_THESE_SUBS_LIST if x.lower() == subreddit.lower()]
    
    if not aSubToBeSkipped:
        for adj in GOOD_ADJS:
            newVoteRecvdFor = checkTheComment(subreddit, respData, adj, diskData, positiveVote=True)
            if newVoteRecvdFor:
                websiteToBeUpdatedForNewVotesOnTheseMods.append(newVoteRecvdFor)
        for adj in BAD_ADJS:
            newVoteRecvdFor = checkTheComment(subreddit, respData, adj, diskData, positiveVote=False)
            if newVoteRecvdFor:
                websiteToBeUpdatedForNewVotesOnTheseMods.append(newVoteRecvdFor)

if websiteToBeUpdatedForNewVotesOnTheseMods:
    myLogger.info("Generating new HTML & pushing to Github")
    generateHTMLAndPushToGithub(websiteToBeUpdatedForNewVotesOnTheseMods)
    myLogger.info("Github push done succyly")
myLogger.info("Script ran succyly.")