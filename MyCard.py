from python_webex.v1.Card import Card


class MyCard(Card):
    def check_if_open_url_button_exists(self):
        actions = self.content[0]["content"]["actions"]
        for action in actions:
            if action["type"] == "Action.OpenURL":
                actions.remove(action)
                
    def add_open_url_action_btn(
        self, title: str = "submit", myUrl: str =  "https://adaptivecards.io/"
    ):
        self.check_if_open_url_button_exists()
        action = {
            "type": "Action.OpenUrl",
            "title": title,
            "url": myUrl
        }
        self.__add_action(action)

    def add_input_number(
            self, input_id:str, input_placeholder: str = None, input_value: str = None
        ):
        self.check_if_id_exists(input_id)
        element = {
            "id": input_id,
            "type": "Input.Number"
        }

        # Webex doesn't support placeholder for input number
        if input_placeholder is not None: element["placeholder"] = input_placeholder 
        if input_value is not None: element["value"] = input_value 
        self.__add_element(element)
    
    def add_input_date(
            self, input_id:str, input_placeholder: str = None, input_value: str = None
        ):
        self.check_if_id_exists(input_id)
        element = {
            "id": input_id,
            "type": "Input.Date"
        }
        
        if input_placeholder is not None: element["placeholder"] = input_placeholder 
        if input_value is not None: element["value"] = input_value 
        self.__add_element(element)
    
    def add_input_time(
            self, input_id:str, input_placeholder: str = None, input_value: str = None
        ):
        self.check_if_id_exists(input_id)
        element = {
            "id": input_id,
            "type": "Input.Time"
        }
        
        if input_placeholder is not None: element["placeholder"] = input_placeholder 
        if input_value is not None: element["value"] = input_value 
        self.__add_element(element)

    def add_input_toggle(
            self, input_id:str, input_title: str = "Default Title"
        ):
        self.check_if_id_exists(input_id)
        element = {
            "id": input_id,
            "type": "Input.Toggle",
            "title": input_title
        }
        self.__add_element(element)

    def add_image(
        self,myUrl: str =  "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Cisco_logo_blue_2016.svg/1200px-Cisco_logo_blue_2016.svg.png"
    ):
        self.check_if_open_url_button_exists()
        element = {
            "type": "Image",
            "url": myUrl
        }
        self.__add_element(element)
    
    def __add_action(self, action_dict):
        self.content[0]["content"]["actions"].append(action_dict)

    def __add_element(self, element_dict):
        self.content[0]["content"]["body"][0]["columns"][0]["items"].append(element_dict)

    def check_if_id_exists(self, id):
        ids = self.get_all_input_ids()
        items = self.content[0]["content"]["body"][0]["columns"][0]["items"]
        if id in ids:
            for item in items:
                if "id" in item.keys():
                    if item['id'] == id:
                        items.remove(item)