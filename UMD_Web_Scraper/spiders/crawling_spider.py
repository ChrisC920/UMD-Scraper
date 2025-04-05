import scrapy
from scrapy import signals
from datetime import datetime
from pytz import timezone
from UMD_Web_Scraper.settings import supabase_client

scraped_data = []

class CrawlingSpider(scrapy.Spider):

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.ending_time = None
        self.starting_time = datetime.now()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(CrawlingSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider, reason):
        tz = timezone('EST')
        today_date = datetime.now(tz).strftime("%Y-%m-%d")

        ending_time = datetime.now()

        # Insert into the food table while referencing the correct foreign keys
        parsed_scraped_data = [{
            "name": data["name"],
            "link": data["link"],
            "serving_size": data["serving_size"],
            "servings_per_container": data["servings_per_container"].replace(" servings per container", ""),
            "calories_per_serving": data["calories_per_serving"].replace("\xa0", ""),
            "total_fat": data["total_fat"],
            "saturated_fat": data["saturated_fat"].replace("\xa0", "").replace("Saturated Fat", ""),
            "trans_fat": data["trans_fat"],
            "total_carbohydrates": data["total_carbohydrates"],
            "dietary_fiber": data["dietary_fiber"].replace("\xa0", "").replace("Dietary Fiber", ""),
            "total_sugars": data["total_sugars"].replace("\xa0", "").replace("Total Sugars", ""),
            "added_sugars": data["added_sugars"].replace("\xa0", "")[9:].replace(" Added Sugars", ""),
            "cholesterol": data["cholesterol"],
            "sodium": data["sodium"],
            "protein": data["protein"]
        } for data in scraped_data]

        # Remove duplicates based on (name, link)
        foods_data = {(data["name"], data["link"]): data for data in parsed_scraped_data}.values()

        food_response = supabase_client.table('foods').upsert(list(foods_data), on_conflict="name, link").execute()

        food_ids = {f["name"]: f["id"] for f in food_response.data}

        dining_halls = list({data["dining_hall"] for data in scraped_data})
        meal_types = list({data["meal_type"] for data in scraped_data})
        sections = list({data["section"].strip() for data in scraped_data})

        dining_hall_response = supabase_client.table('dining_halls').upsert(
            [{"name": dh.strip()} for dh in dining_halls], on_conflict="name"
        ).execute()

        meal_type_response = supabase_client.table('meal_types').upsert(
            [{"name": mt.strip()} for mt in meal_types], on_conflict="name"
        ).execute()

        section_response = supabase_client.table('sections').upsert(
            [{"name": sec.strip()} for sec in sections], on_conflict="name"
        ).execute()

        date_response = supabase_client.table('dates').upsert({"date": today_date}, on_conflict="date").execute()

        dining_hall_ids = {d["name"]: d["id"] for d in dining_hall_response.data}
        meal_type_ids = {m["name"]: m["id"] for m in meal_type_response.data}
        section_ids = {s["name"]: s["id"] for s in section_response.data}
        date_ids = {da["date"]: da["id"] for da in date_response.data}

        food_dining_halls = [
            {"food_id": food_ids[data["name"]], "dining_hall_id": dining_hall_ids[data["dining_hall"].strip()]}
            for data in scraped_data
        ]

        food_meal_types = [
            {"food_id": food_ids[data["name"]], "meal_type_id": meal_type_ids[data["meal_type"].strip()]}
            for data in scraped_data
        ]

        food_sections = [
            {"food_id": food_ids[data["name"]], "section_id": section_ids[data["section"].strip()]}
            for data in scraped_data
        ]

        food_dates = [
            {"food_id": food_ids[data["name"]], "date_id": date_ids[today_date]}
            for data in scraped_data
        ]

        unique_food_dining_halls = list(
            {(entry["food_id"], entry["dining_hall_id"]): entry for entry in food_dining_halls}.values())
        unique_food_meal_types = list(
            {(entry["food_id"], entry["meal_type_id"]): entry for entry in food_meal_types}.values())
        unique_food_sections = list(
            {(entry["food_id"], entry["section_id"]): entry for entry in food_sections}.values())
        unique_food_dates = list(
            {(entry["food_id"], entry["date_id"]): entry for entry in food_dates}.values())

        supabase_client.table('food_dining_halls').upsert(unique_food_dining_halls).execute()
        supabase_client.table('food_meal_types').upsert(unique_food_meal_types).execute()
        supabase_client.table('food_sections').upsert(unique_food_sections).execute()
        supabase_client.table('food_dates').upsert(unique_food_dates).execute()

        dining_hall_sections = [
            {"dining_hall_id": dining_hall_ids[data["dining_hall"].strip()], "section_id": section_ids[data["section"].strip()]}
            for data in scraped_data
        ]

        unique_dining_hall_sections = list(
            {(entry["dining_hall_id"], entry["section_id"]): entry for entry in dining_hall_sections}.values()
        )

        supabase_client.table('dining_hall_sections').upsert(
            unique_dining_hall_sections, on_conflict="dining_hall_id, section_id"
        ).execute()

        allergen_names = list({allergen for data in scraped_data for allergen in data["allergens"]})
        allergen_response = supabase_client.table('allergens').upsert(
            [{"name": a} for a in allergen_names], on_conflict="name"
        ).execute()

        allergen_ids = {a["name"]: a["id"] for a in allergen_response.data}

        food_allergens = [
            {"food_id": food_ids[data["name"]], "allergen_id": allergen_ids[allergen]}
            for data in scraped_data for allergen in data["allergens"]
        ]

        unique_food_allergens = list(
            {(entry["food_id"], entry["allergen_id"]): entry for entry in food_allergens}.values())

        supabase_client.table('food_allergens').upsert(unique_food_allergens).execute()

        food_relations_data = [{"food_id": food_ids[data["name"]], "dining_hall_id": dining_hall_ids[data["dining_hall"].strip()], "date_id": date_ids[today_date], "meal_type_id": meal_type_ids[data["meal_type"].strip()], "section_id": section_ids[data["section"].strip()]}
            for data in scraped_data]

        food_relations = supabase_client.table('food_relations').upsert(food_relations_data).execute()

        print(f"Scraped {len(scraped_data)} items.")
        print("Time taken:", ending_time - self.starting_time)

    tz = timezone('EST')
    today_date = datetime.now(tz).strftime("%m/%d/%Y")
    # today_date = "3/30/2025"
    name = "mycrawler"
    allow_domains = ["nutrition.umd.edu"]
    start_urls = [f"https://nutrition.umd.edu/?locationNum=19&dtdate={today_date}",
                  f"https://nutrition.umd.edu/?locationNum=51&dtdate={today_date}",
                  f"https://nutrition.umd.edu/?locationNum=16&dtdate={today_date}"]

    def parse(self, response, **kwargs):
        dining_hall = response.url[39:41]
        if dining_hall == "51":
            dining_hall = "251 North"
        elif dining_hall == "19":
            dining_hall = "Yahentamitsi"
        elif dining_hall == "16":
            dining_hall = "South"
        else:
            dining_hall = "Unknown"

        num_meal_types = len(response.css(".tab-pane").getall())
        meal_type_list = []
        if num_meal_types == 3:
            breakfast_type = response.css("#pane-1")
            lunch_type = response.css("#pane-2")
            dinner_type = response.css("#pane-3")
            meal_type_list.append(breakfast_type)
            meal_type_list.append(lunch_type)
            meal_type_list.append(dinner_type)
        elif num_meal_types == 2:
            brunch_type = response.css("#pane-1")
            dinner_type = response.css("#pane-2")
            meal_type_list.append(brunch_type)
            meal_type_list.append(dinner_type)

        for meal_type in meal_type_list:
            section_list = meal_type.css(".card-body")
            for curr_section in section_list:
                section = curr_section.css("h5.card-title::text").get()
                rows = curr_section.css(".menu-item-row")
                for row in rows:
                    allergens = row.css(".nutri-icon::attr(title)").getall()
                    item = row.css(".menu-item-name")
                    link = "https://nutrition.umd.edu/" + item.css("::attr(href)").get()
                    yield response.follow(link, callback=self.parse_item,
                                          cb_kwargs={"section": section, "dining_hall": dining_hall, "meal_type": meal_type, "num_meal_types": num_meal_types, "allergens": allergens})

    @staticmethod
    def parse_item(response, section, dining_hall, meal_type, num_meal_types, allergens):
        item = {
            "name": response.css("h2::text").get().title(),
            "dining_hall": dining_hall,
            "meal_type": convert_meal_type(meal_type, num_meal_types),
            "section": section,
            "link": response.url,
            "serving_size": response.css(".nutfactsservsize::text")[1].get().lower(),
            "servings_per_container": response.css(".nutfactsservpercont::text").get().lower(),
            "calories_per_serving": response.css("td p::text")[1].get(),
            "total_fat": response.css(".nutfactstopnutrient::text")[0].get(),
            "saturated_fat": response.css(".nutfactstopnutrient::text")[2].get(),
            "trans_fat": response.css(".nutfactstopnutrient *::text")[4].get(),
            "total_carbohydrates": response.css(".nutfactstopnutrient::text")[1].get(),
            "dietary_fiber": response.css(".nutfactstopnutrient::text")[3].get(),
            "total_sugars": response.css(".nutfactstopnutrient::text")[6].get(),
            "added_sugars": response.css(".nutfactstopnutrient::text")[8].get(),
            "cholesterol": response.css(".nutfactstopnutrient::text")[7].get(),
            "sodium": response.css(".nutfactstopnutrient::text")[9].get(),
            "protein": response.css(".nutfactstopnutrient::text")[10].get(),
            "allergens": allergens
        }
        scraped_data.append(item)


def convert_meal_type(meal_type_selector, num_meal_types):
    meal_type_id = meal_type_selector.attrib["id"]
    if num_meal_types == 3:
        if meal_type_id == 'pane-1':
            return 'Breakfast'
        elif meal_type_id == 'pane-2':
            return 'Lunch'
        elif meal_type_id == 'pane-3':
            return 'Dinner'
    else:
        if meal_type_id == 'pane-1':
            return 'Brunch'
        elif meal_type_id == 'pane-2':
            return 'Dinner'
    raise Exception('Unknown meal')
