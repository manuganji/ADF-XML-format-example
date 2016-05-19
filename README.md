# ADF-XML-format-example
Overview
------------------
A short Django View file example to implement ADF XML format. Auto lead Data Format is the standard way to collect and communicate lead data between systems in the Automotive Dealerships. [This](http://www.entmerch.org/programsinitiatives/the-ema-metadata-structure/autolead_data_format.pdf) is the best document to read up more about it.

Util functions can be used as standalone with minor refactoring.

To add a new form, the ADFFormView has to be subclassed and `adfxml` method has to be implemented in the child. The method signature is `adfxml(self, form, prospect_node)`. `prospect_node` is a `etree.Element` object. Refer to the existing FormViews to get an idea of how the class works.

Twilio support also present to send the vehicle information in an SMS to the customer and simulateneously log the lead in the CRM via ADF XML support.

Requirements
------------------

- `django`
- `lxml`
- `twilio`

Goals for this Repo
---------------------

I'm uploading some work I did in my previous project. I tested this with [VinSolutions](http://www.vinsolutions.com/) one of the popular CRMs used in this industry. If there is enough interest, I could

- Refine the architecture and dependency on Django
- Make it a standalone library 
- Add tests

Suggestions welcome.
