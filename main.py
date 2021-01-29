import discord
from discord.ext import commands
import requests
import json
from tabulate import tabulate
import asyncio

token = 'YOUR BOT TOKEN'
client = commands.Bot(command_prefix = '.')
selected = 0
numResults = 0

# Potentially useful endpoints; requires login:
# https://www.goat.com/api/v1/product_templates/{SLUG}/offer_data_v2?size={SIZE}
# https://www.goat.com/api/v1/wants/find_offer?productTemplateId={ID}&size={SIZE}

# Sort of useless endpoints:
# https://www.goat.com/api/v1/product_variants?productTemplateId={SLUG/ID}

async def lookup(selection, keywords, ctx):
    json_string = json.dumps({"params": f"distinct=true&facetFilters=()&facets=%5B%22size%22%5D&hitsPerPage=20&numericFilters=%5B%5D&page=0&query={keywords}"})
    byte_payload = bytes(json_string, 'utf-8')
    params = {
        "x-algolia-agent": "Algolia for vanilla JavaScript 3.25.1", 
        "x-algolia-application-id": "2FWOTDVM2O", 
        "x-algolia-api-key": "ac96de6fef0e02bb95d433d8d5c7038a"
    }
    header = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'accept-language': 'en-us',
        'accept-encoding': 'br,gzip,deflate'
    }
    with requests.Session() as s:
        r = s.post("https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_v2/query", params=params, verify=False, data=byte_payload, timeout=30)
    results = r.json()["hits"][selection]
    generalAPI = f"https://www.goat.com/api/v1/product_templates/{results['slug']}/show_v2"
    sellAPI = f"https://www.goat.com/api/v1/product_variants?productTemplateId={results['slug']}&shoeCondition=new_no_defects&boxCondition=good_condition"
    offerAPI = f"https://www.goat.com/api/v1/highest_offers?productTemplateId={results['id']}"
    askAPI = f"https://www.goat.com/api/v1/product_variants?productTemplateId={results['slug']}"
    general = requests.get(generalAPI, headers=header).json()
    asks = requests.get(sellAPI, headers=header).json()
    bids = requests.get(offerAPI, headers=header).json()
    asks = requests.get(askAPI, headers=header).json()
    link = f"https://goat.com/sneakers/{results['slug']}"

    priceDict = {}
    for size in general['sizeOptions']:
            priceDict[float(size["value"])] = {"ask": 0, "bid": 0}
    for ask in asks:
        if ask["size"] in priceDict:
            priceDict[ask["size"]]["ask"] = str(ask["lowestPriceCents"]["amountUsdCents"])[:-2]
    for bid in bids:
        if bid["size"] in priceDict:
            priceDict[bid["size"]]["bid"] = str(bid["offerAmountCents"]["amountUsdCents"])[:-2]
    for ask in asks:
        if ask["boxCondition"] == "good_condition":
            priceDict[ask["size"]]["ask"] = str(ask["lowestPriceCents"]["amountUsdCents"])[:-2]

    if general["productCategory"] == "clothing":
        priceDict2 = {}
        for size in priceDict:
            for size2 in general["sizeOptions"]:
                if size == size2["value"]:
                    priceDict2[size2["presentation"].upper()] = priceDict[size]
        priceDict = priceDict2

    priceDict = {k: v for k,v in priceDict.items() if v["ask"] != 0 or v["bid"] != 0}

    table = []
    table.append(["Size", "Lowest Ask", "Highest Bid"])
    for size, price in priceDict.items():
        table.append([size, f"${price['ask']}", f"${price['bid']}"])

    tabulated = "```" + tabulate(table, headers="firstrow", numalign="center", stralign="center", tablefmt="simple") + "```"

    embed = discord.Embed(title='GOAT App Price Checker', color=0x13e79e)
    embed.set_thumbnail(url=general['mainGlowPictureUrl'])
    embed.set_footer(text='https://github.com/kxvxnc')
    embed.add_field(name='Product Name', value=f"[{general['name']}]({link})", inline=False)
    embed.add_field(name='SKU', value=f"{general['sku']}", inline=True)
    try:
        embed.add_field(name='Release Date', value=f"{results['release_date'].split('T')[0]}", inline=True)
    except:
        embed.add_field(name='Release Date', value=f"{results['release_date']}", inline=True)
    embed.add_field(name='Prices', value=tabulated, inline=False)
    await ctx.send(embed=embed)

@client.event
async def on_ready():
    print('GOAT Discord Bot is ready.')

@client.command(pass_context=True)
async def logout(ctx):
    await client.logout()

@client.command(pass_context=True)
async def goat(ctx, *args):
    keywords = ''
    for word in args:
        keywords += word + '%20'
    json_string = json.dumps({"params": f"distinct=true&facetFilters=()&facets=%5B%22size%22%5D&hitsPerPage=20&numericFilters=%5B%5D&page=0&query={keywords}"})
    byte_payload = bytes(json_string, 'utf-8')
    params = {
        "x-algolia-agent": "Algolia for vanilla JavaScript 3.25.1", 
        "x-algolia-application-id": "2FWOTDVM2O", 
        "x-algolia-api-key": "ac96de6fef0e02bb95d433d8d5c7038a"
    }
    with requests.Session() as s:
        r = s.post("https://2fwotdvm2o-dsn.algolia.net/1/indexes/product_variants_v2/query", params=params, verify=False, data=byte_payload, timeout=30)
        numResults = len(r.json()["hits"])
        results = r.json()["hits"]

    emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        
    def check(reaction, user):
        if str(reaction.emoji) in emojis:
            global selected 
            selected = emojis.index(str(reaction.emoji))
        return user == ctx.author and str(reaction.emoji) in emojis

    if numResults == 1:
        await lookup(0, keywords, ctx)
    elif numResults >= 2 and numResults <= 10:
        resultsText = ""
        for i in range(len(results)):
            resultsText += f"{i + 1}. {results[i]['name']}\n"
        msg = await ctx.send('Multiple products found. React to select the correct product:\n' + "```" + resultsText + "```")
        for i in range(len(results)):
            await msg.add_reaction(emojis[i])
        try:
            await client.wait_for('reaction_add', timeout=30.0, check=check)
            await lookup(selected, keywords, ctx)
            # This automatically deletes the selection message
            # await msg.delete()
        except asyncio.TimeoutError:
            await ctx.send('Took too long to select an option. Please try again.')
    elif numResults == 0:
        await ctx.send('No products found. Please try again.')
    elif numResults > 10:
        await ctx.send('Too many products found. Please try again.')

if __name__ == "__main__":
    client.run(token)
