from lxml import etree

class CyclusFuelCycle(object):
    """ simple holding class for the fuel cycle in cyclus input. underlying
    representation is in xml. The constructor takes info, an xml node
    representation of simulation information, initial conditions, a list of xml
    nodes that state the ICs, and a growth structure, which is a dictionary of
    commodity demands whose values are a list of xml nodes that construct the
    piecewise demand function describing that commodity demand.
    """
    def __init__(self, info, initial_conditions, growth, producers):
        self.info = info
        self.initial_conditions = initial_conditions
        self.growth = growth
        self.producers = producers

class ExtraneousFCInfo(object):
    """This is a container class that holds fuel cycle information required to
    complete a Cyclus input file that is not directly related to the fuel cycle
    specification. An example of such information is a mapping from facility
    names or types in the specifications to specific Cyclus agent classes.
    """
    def __init__(self, fac_type_map):
        # add additional objects to this interface as needed
        self.fac_type_map = fac_type_map

class SupportError(Exception):
    """Error for unsupported operations"""
    pass

class JsonFuelCycleParser(object):
    """ A parser that accepts a python-based json object representation of
    the fuel cycle from the FCS benchmark specification language and returns a
    cyclus-based representation of the fuel cycle
    """
    def __init__(self, description, extra_info):
        """ Fuel Cycle parser constructor. Note that the additional argument
        extra_info provides an interface to the additional information required
        to complete a Cyclus fuel cycle description that is not required in the
        specification language.
        """
        self.__description = description
        self.__extra_info = extra_info
        self.__default_agent_types = self.__getDefaultAgents()

    def __getDefaultParameters(self):
        """This method provides the default simulation parameters as currently
        used in Cyclus simulations.
        """
        params = {}
        params["startmonth"] = "1"
        params["startyear"] = "2000"
        params["simstart"] = "0"
        params["decay"] = "2"        
        return params

    def __getDefaultAgents(self):
        """This method provides the default mapping between basic facility
        types and their representation in Cyclus
        """
        default_agents = {}
        default_agents["reactor"] = "BatchReactor"
        default_agents["repository"] = "SinkFacility"
        default_agents["enrichment"] = "EnrichmentFacility"
        default_agents["mine"] = "SourceFacility"
        return default_agents

    def __duration(self):
        """A simple method to automate the determiniation of the simulation
        duration.
        """
        units = self.__description["attributes"]["grid"]
        time = self.__description["constraints"]["grid"]
        diff = time[1] - time[0]
        if units is "years":
            diff *= 12
        return diff

    def __constructSimInfo(self):
        """Constructs the control block, describing basic simulation parameters
        """
        root = etree.Element("control")
        duration = etree.SubElement(root,"duration")
        duration.text = str(self.__duration())
        defaults = self.__getDefaultParameters()
        startmonth = etree.SubElement(root,"startmonth")
        startmonth.text = defaults["startmonth"]
        startyear = etree.SubElement(root,"startyear")
        startyear.text = defaults["startyear"]
        simstart = etree.SubElement(root,"simstart")
        simstart.text = defaults["simstart"]
        decay = etree.SubElement(root,"decay")
        decay.text = defaults["decay"]
        return root

    def __constructInitialCondition(self):
        """Constructs the xml structure of initial condition entries"""
        root = None
        if "initialConditions" in self.__description["attributes"]:
            initial_conditions = \
                self.__description["attributes"]["initialConditions"]
            root = etree.Element("initialfacilitylist")
            fac_type_map = self.__extra_info.fac_type_map
            for name, amount in initial_conditions.iteritems():
                fac_t = fac_type_map[name]
                entry = etree.SubElement(root,"entry")
                prototype = etree.SubElement(entry,"prototype")
                prototype.text = self.__default_agent_types[fac_t]
                number = etree.SubElement(entry,"number")
                number.text = str(amount)
        return root

    def __addGrowthNode(self,root,dem_t,values):
        """Constructs a single demand node
        """
        demand = etree.SubElement(root,"demand")
        eltype = etree.SubElement(demand,"type")
        eltype.text = dem_t
        params = etree.SubElement(demand,"parameters")
        params.text = str(values["slope"]) 
        if "startValue" in values:
            params.text +=  " " +str(values["startValue"])
        else:
            params.text += " 0"
        time = etree.SubElement(demand,"start_time")
        time.text = str(values["startTime"])

    def __constructGrowth(self):
        """Constructs a GrowthRegion xml node of growth curve information"""
        root = etree.Element("GrowthRegion")
        dic = self.__description["constraints"]["demands"]
        for key in dic.iterkeys():
            if dic[key]["growth"]["type"] is not "linear":
                raise SupportError("Only linear functions currently supported")
            commod = etree.SubElement(root,"commodity")
            name = etree.SubElement(commod,"name")
            name.text = key
            n = len(dic[key]["growth"]) - 1
            for i in range(n):
                name = "period" + str(i+1)
                self.__addGrowthNode(commod,"linear",dic[key]["growth"][name])
        return root

    def __constructProducers(self):
        """Constructs a dictionary of commodities and which facilities produce
        that commodity
        """
        params = self.__description["attributes"]["demands"]
        producers = {key: value[1] for key, value in params.iteritems()}
        return producers

    def parse(self):
        """Given a python dictionary of the fuel cycle as specified in the
        benchmark specification language and additional Cyclus-specific
        information (provided in the constructor), returns the corresponding
        CyclusFuelCycle object.
        """
        info = self.__constructSimInfo()
        ics = self.__constructInitialCondition()
        growth = self.__constructGrowth()
        producers = self.__constructProducers()
        return CyclusFuelCycle(info, ics, growth, producers)