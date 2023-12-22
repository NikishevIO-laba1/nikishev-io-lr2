import yaml

def yaml_load(file):
    with open(file, 'r', encoding = 'utf8') as f: return yaml.safe_load(f.read())


def tolist(x, dtype = int):
    if isinstance(x, (int, float)): return [x]
    if isinstance(x, str): return [dtype(i) for i in x.replace(' ', '').split(',')]
    else: return list(x)
    

questions = yaml_load('вопросы.yaml')
objects = yaml_load('объекты.yaml')
rules = yaml_load('правила.yaml')

production_rules = yaml_load('продукционные правила.yaml')


class QA:
    def __init__(self, questions=questions, objects=objects, rules=rules, production_rules = production_rules):
        self.questions = questions
        
        self.rules = rules
        
        self.objects = objects
        
        self.production_rules = production_rules


        self.attributes = {}
        
        self.questions_remaining = set([1])
        for i in self.questions.values():
            if 'параметр' in i: i['атрибут'] = i['параметр']
        for i in self.rules.values():
            if 'параметры' in i: i['атрибуты'] = i['параметры'] 
        self.current_question_id = 1
        self.objects_matching = self.objects.copy()

        self.questions_excluded = set([])

    def condition(self, attr, cond):
        """Проверяет условие для правил"""
        if attr not in self.attributes: return False
        if isinstance(cond, str) and cond.startswith('УСЛОВИЕ '):
            if cond.endswith('+'):
                return self.attributes[attr] >= float(cond[8:-1])
            return self.attributes[attr] <= float(cond[8:-1])
        elif isinstance(cond, list):
            for i in cond:
                if i in self.attributes[attr]: return True
            return False
        else: return cond in self.attributes[attr]


    def check_rule(self, rule_id):
        """Обновляет оставшиеся вопросы согласно правилу"""
        assert rule_id in self.rules, f'Правило {rule_id} не существует'
        rule = self.rules[rule_id]

        matches = True
        for k, v in rule['атрибуты'].items():
            if not self.condition(k, v):
                matches = False
                break
        
        if matches:
            if 'включить' in rule: self.questions_remaining.update(tolist(rule['включить']))
            if 'пропустить' in rule: self.questions_excluded.update(tolist(rule['пропустить']))
        
        return matches
    
    def check_rules(self):
        """Проверяет все правила"""
        for i in self.rules.keys(): self.check_rule(i)
        for i in self.questions_remaining.copy():
            if i in self.questions_excluded: self.questions_remaining.remove(i)

    def check_production_rule(self, id):
        # print(self.attributes)
        # >> {'цель приобретения': {'Для офиса'}, 'цена': {'УСЛОВИЕ 1.0-'}, 'беспроводной режим': {True}, 
        # >> 'эргономичность': {True}, 'приоритет': {'Скорость печати'}, 'тип клавиатуры': {'мембранная'}, 
        # >> 'профиль': {'низкопрофильная'}, 'искривлённая': {True}, 'Bluetooth': {True}, 'кол-во устройств': {'УСЛОВИЕ 1.0+'}, 
        # >> 'материал кнопок': {'ABS'}, 'ножки': {True}, 'максимальный наклон': {'УСЛОВИЕ 1.0+'}}
        prod_rule_dict = self.production_rules[id]
        premise = prod_rule_dict['посылка'] # посылка
        premises_match = [True]*len(premise)
        premise_i = 0
        for premise_attribute, premise_value in premise.items():
            if premise_attribute in self.attributes:
                for condition in self.attributes[premise_attribute]:
                    if isinstance(condition, str) and condition.startswith('УСЛОВИЕ '):
                        if condition.endswith('+'):
                            if float(premise_value[:-1]) < float(condition[8:-1]): premises_match[premise_i] = False
                        if condition.endswith('-'):
                            if float(premise_value[:-1]) > float(condition[8:-1]): premises_match[premise_i] = False
                    else:
                        if premise_value is False and premise_value not in self.attributes[premise_attribute]: premises_match[premise_i] = False
            premise_i += 1
            
        if len(premise) == 1: operator = 'AND'
        else: 
            operator = prod_rule_dict['операция']

        if operator == 'AND':
            if all(premises_match):
                matches = True
            else: matches = False
        
        if operator == 'OR':
            if any(premises_match):
                matches = True
            else: matches = False
        
        if matches:
            for conseq_attribute, conseq_value in prod_rule_dict['следствие'].items():
                self.attributes[conseq_attribute] = set([conseq_value])
                
                
    def check_object(self, object_id):
        """Проверяет, подходит ли объект"""
        assert object_id in self.objects, f'Объект {object_id} не существует'
        obj = self.objects[object_id]
        matches = True
        

        
        for obj_attr,obj_value in obj.items():

            # Проверяется атрибут объекта
            if obj_attr in self.attributes:
                for condition in self.attributes[obj_attr]:
                    if isinstance(condition, str) and condition.startswith('УСЛОВИЕ '):
                        if condition.endswith('+'):
                            if obj_value < float(condition[8:-1]): matches = False
                        if condition.endswith('-'):
                            if obj_value > float(condition[8:-1]): matches = False
                    else:
                        if obj_value is False and obj_value not in self.attributes[obj_attr]: matches = False
        return matches

    def check_objects(self):
        """Выдаёт все объекты соответствующие ответам"""
        objects_matched = []
        for i in self.objects.keys():
            if self.check_object(i): objects_matched.append(i)
        return objects_matched
    
    def ask(self, question_id = None):
        """Задаётся один вопрос"""

        if question_id is None: question_id = self.current_question_id
        assert question_id in self.questions, f'Вопрос {question_id} не существует'
        assert question_id not in self.questions_excluded, f'Вопрос {question_id} иключён или уже задан'

        question = self.questions[question_id]
        self.questions_excluded.add(question_id)

        attribute = question['атрибут'] if 'атрибут' in question else None

        # Задаётся вопрос
        print()
        #print(self.attributes)
        #print(self.questions_excluded)
        #print(self.questions_remaining)
        print(f"{question_id}: {question['вопрос']}")
        if 'выбор' in question['тип']:

            # Вывод ответов
            for i, v in enumerate(question['ответы'].keys() if isinstance(question['ответы'], dict) else question['ответы']):
                print(f'{i+1}: {v}')

            # Ответ
            answer = False
            while type(answer) == bool:
                try:
                    answer = tolist(input('Введите числа ответов через запятую: ' if 'множ' in question['тип'] else 'Введите число ответа: '))
                except: 
                    print('Ошибка в ответе, попробуйте ещё раз.')
            
            # Обработка
            if answer != 0:
                for i, v in enumerate(question['ответы'].items() if isinstance(question['ответы'], dict) else question['ответы']):
                    if i+1 in answer:
                        #print(v, type(v))
                        if 'атриб' not in question['тип']:
                            if attribute: 
                                if attribute not in self.attributes: self.attributes[attribute] = set()
                                self.attributes[attribute].add(v[0] if isinstance(v,tuple) else v)
                            if isinstance(v, tuple):
                                for attr,value in v[1].items():
                                    if attr not in self.attributes: self.attributes[attr] = set()
                                    if isinstance(value, list): self.attributes[attr].update(set(value))
                                    else: self.attributes[attr].add(f'УСЛОВИЕ {value}' if (isinstance(value, str) and value.endswith(('+', '-'))) else value)
                        else:
                            self.attributes[v] = set([True])
    
        elif question['тип'] == 'да/нет':
            assert attribute, f'Вопрос {question_id} в форме `да/нет` должен иметь поле `атрибут` или `параметр`'
            print('1: Да\n2: Нет')
            answer = False
            while type(answer) == bool:
                try:
                    answer = int(input('Введите число ответа: '))
                except: 
                    print('Ошибка в ответе, попробуйте ещё раз.')
            if answer == 1: self.attributes[attribute] = set([True])
            if answer == 2: self.attributes[attribute] = set([False])
        
        elif 'ввод' in question['тип']:
            assert attribute, f'Вопрос {question_id} в форме `ввод` должен иметь поле `атрибут` или `параметр`'
            answer = False
            while type(answer) == bool:
                try:
                    answer = float(input('Введите ваш ответ в виде числа: '))
                except: 
                    print('Ошибка в ответе, попробуйте ещё раз.')
            if answer != 0:
                if attribute not in self.attributes: self.attributes[attribute] = set()
                if 'макс' in question['тип']: self.attributes[attribute].add(f'УСЛОВИЕ {answer}-')
                else: self.attributes[attribute].add(f'УСЛОВИЕ {answer}+')

        # Определение следующего вопроса
        self.check_rules()
        if 'следующий вопрос' in question: 
            if question['следующий вопрос'] not in self.questions_excluded:
                self.current_question_id = question['следующий вопрос']
            else:
                self.current_question_id = list(self.questions_remaining)[0] if len(self.questions_remaining) > 0 else None
        else:
            self.current_question_id = list(self.questions_remaining)[0] if len(self.questions_remaining) > 0 else None
                        
        return self.current_question_id

    def run(self):
        while True:
            if not self.ask(): break
        for i in self.production_rules: self.check_production_rule(i)
        matches = self.check_objects()
        print()
        if len(matches)>0:
            n = '\n'
            print(f'Вам подходят следующие клавиатуры:{n}{n.join(matches)}')
        else: 
            print('По вашим ответам не найдено клавиатур.')

keyboards = QA()
keyboards.run()