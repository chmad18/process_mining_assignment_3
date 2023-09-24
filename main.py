import xml.etree.ElementTree as ET
import datetime
import json


class Place:
    def __init__(self, id, name):
        self.id = id
        self.tokens = 0
        self.name = name


class Transition:
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.inGoing = []
        self.outGoing = []

    def addOutGoingEdge(self, place):
        self.outGoing.append(place)

    def addInGoingEdge(self, place):
        self.inGoing.append(place)

    def isEnabled(self):
        isEnabled = True
        if len(self.inGoing) > 0:
            for p in self.inGoing:
                place: Place = p
                if not place.tokens >= 1:
                    isEnabled = False
        else:
            return False
        return isEnabled

    def subtractFromInGoing(self):
        for p in self.inGoing:
            place: Place = p
            place.tokens -= 1

    def addToOutGoing(self):
        for p in self.outGoing:
            place: Place = p
            place.tokens += 1

    def fire(self):
        if self.isEnabled():
            self.subtractFromInGoing()
            self.addToOutGoing()


class PetriNet:
    def __init__(self):
        self.places = {}
        self.transitions = {}

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    def add_place(self, id, name):
        bool = True
        for key in self.places:
            if self.places.get(key).name == name:
                bool = False
        if bool:
            self.places.update({id: Place(id, name)})

    def add_transition(self, name, id):
        self.transitions.update({id: Transition(name, id)})

    def add_edge(self, source, target):
        if source > 0:
            place: Place = self.places.get(source)
            transition: Transition = self.transitions.get(target)
            transition.addInGoingEdge(place)
            return self
        else:
            place: Place = self.places.get(target)
            transition: Transition = self.transitions.get(source)
            transition.addOutGoingEdge(place)
            return self

    def get_tokens(self, place):
        return self.places.get(place).tokens

    def is_enabled(self, transition):
        transition: Transition = self.transitions.get(transition)
        return transition.isEnabled()

    def add_marking(self, place):
        self.places.get(place).addToken(1)

    def fire_transition(self, t):
        if self.is_enabled(t):
            transition: Transition = self.transitions.get(t)
            transition.fire()

    def transition_name_to_id(self, name):
        # print(self.toJSON())
        for t in self.transitions:
            transition: Transition = self.transitions.get(t)
            tname = transition.name
            if tname == name:
                return transition.id


def read_from_file(filename):
    result = {}
    tree = ET.parse(filename)
    root = tree.getroot()
    for trace in root.findall(".//{http://www.xes-standard.org/}trace"):
        trace_name = trace.find("{http://www.xes-standard.org/}string[@key='concept:name']").get("value")
        for event in trace.findall("{http://www.xes-standard.org/}event"):
            resource = event.find("{http://www.xes-standard.org/}string[@key='org:resource']").get("value")
            cost = int(event.find("{http://www.xes-standard.org/}int[@key='cost']").get("value"))
            concept_name = event.find("{http://www.xes-standard.org/}string[@key='concept:name']").get("value")
            timestamp_str = event.find("{http://www.xes-standard.org/}date[@key='time:timestamp']").get("value")
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S%z")
            timestamp_formatted = timestamp.replace(tzinfo=None)

            if trace_name in result:
                result.get(trace_name).append({
                    "org:resource": resource,
                    "cost": cost,
                    "concept:name": concept_name,
                    "time:timestamp": timestamp_formatted
                })
            else:
                result[trace_name] = [
                    {
                        "org:resource": resource,
                        "cost": cost,
                        "concept:name": concept_name,
                        "time:timestamp": timestamp_formatted
                    }
                ]
    return result


def alpha(log):
    # Step 1: Extract the set of transitions from the log
    transitions = set(event["concept:name"] for trace in log.values() for event in trace)

    # Step 2: Identify causal dependencies between transitions
    causal_relations = {}  # A dictionary to hold causal relations
    for trace in log.values():
        for i in range(len(trace) - 1):
            src = trace[i]["concept:name"]
            tgt = trace[i + 1]["concept:name"]
            if src not in causal_relations:
                causal_relations[src] = set()
            causal_relations[src].add(tgt)

    # Step 3: Create the Petri net
    petri_net = PetriNet()
    place_id_counter = 1
    transition_id_counter = -1

    for transition_name in transitions:
        transition_id = transition_id_counter
        transition_id_counter -= 1
        petri_net.add_transition(transition_name, transition_id)

    for src, tgts in causal_relations.items():
        for tgt in tgts:
            # Create a place for each causal relation
            place_id = place_id_counter
            place_id_counter += 1
            petri_net.add_place(place_id, f"place_{place_id}")

            # Connect the transitions to the place based on the causal relation
            src_transition_id = petri_net.transition_name_to_id(src)
            tgt_transition_id = petri_net.transition_name_to_id(tgt)
            petri_net.add_edge(src_transition_id, place_id)
            petri_net.add_edge(place_id, tgt_transition_id)

    return petri_net

if __name__ == '__main__':
    # Reading the event log from a file
    mined_model = alpha(read_from_file("extension-log.xes"))

    def check_enabled(pn: PetriNet):
        ts = ["record issue", "inspection", "intervention authorization", "action not required", "work mandate",
              "no concession", "work completion", "issue completion"]
        for t in ts:
            print(pn.is_enabled(pn.transition_name_to_id(t)))
        print("")


    # Example traces to check the enabled transitions and fire them
    trace = ["record issue", "inspection", "intervention authorization", "work mandate", "work completion",
             "issue completion"]
    for a in trace:
        check_enabled(mined_model)
        mined_model.fire_transition(mined_model.transition_name_to_id(a))
