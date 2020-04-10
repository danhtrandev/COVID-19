import streamlit as st
from model_utils import *

st.title('Covid-19 Prognosis using death cases')


def main(scope, local, lockdown_date, forecast_fun, debug_fun, metrics, show_debug, show_data):
    data_load_state = st.text('Forecasting...')
    try:
        daily, cumulative = forecast_fun(local, lockdown_date=lockdown_date)
    except ValueError:
        st.error('Not enough data to provide prognosis, please check input lockdown date')
        return None
    data_load_state.text('Forecasting... done!')

    st.subheader('Daily')
    st.line_chart(daily[metrics])

    st.subheader('Cumulative')
    st.line_chart(cumulative[metrics])

    log_fit = debug_fun(local, lockdown_date=lockdown_date)
    if show_debug:
        st.subheader('Fitted log of daily death before and after lock down being effective')
        st.line_chart(log_fit)
    if show_data:
        st.subheader('Raw Data')
        st.write('Daily metrics', daily)
        st.write('Cumulative metrics', cumulative)

scope = st.sidebar.selectbox('Country or US State', ['Country', 'State'], index=0)
if scope=='Country':
    #data_load_state = st.text('Loading data...')
    death_data = get_global_death_data()
    #data_load_state.text('Loading data... done!')
    local = st.sidebar.selectbox('Which country do you like to see prognosis', death_data.Country.unique(), index=156)
    lockdown_date = st.sidebar.date_input('When did full lockdown happen? Very IMPORTANT to get accurate prediction',
                                          get_lockdown_date_by_country(local))
    forecast_fun = get_metrics_by_country
    debug_fun = get_log_daily_predicted_death_by_country
else:
    #data_load_state = st.text('Loading data...')
    death_data = get_US_death_data()
    #data_load_state.text('Loading data... done!')
    local = st.sidebar.selectbox('Which US state do you like to see prognosis', death_data.State.unique(), index=9)
    lockdown_date = st.sidebar.date_input('When did full lockdown happen? Very IMPORTANT to get accurate prediction',
                                          get_lockdown_date_by_state_US(local))
    forecast_fun = get_metrics_by_state_US
    debug_fun = get_log_daily_predicted_death_by_state_US



'You selected: ', local, 'with lock down date: ', lockdown_date
metrics = st.sidebar.multiselect('Which metrics you like to plot?',
                        ('death', 'predicted_death', 'infected', 'symptomatic',
                         'hospitalized', 'ICU', 'hospital_beds'),
                        ['death', 'predicted_death', 'ICU'])
show_debug = st.sidebar.checkbox('Show fitted log death')
show_data = st.sidebar.checkbox('Show raw data')
if st.sidebar.button('Run'):
    main(scope, local, lockdown_date, forecast_fun, debug_fun, metrics, show_debug,show_data)

if st.checkbox('Show authors'):
    st.subheader('Authors')
    st.markdown('Quoc Tran - Principal Data Scientist - WalmartLabs.')
    st.markdown('Huong Huynh - Data Scientist - Virtual Power Systems.')
    st.markdown('Feedback: hthuongsc@gmail.com')
if st.checkbox('Show Datasource'):
    st.markdown('https://coronavirus.jhu.edu/map.html')
if st.checkbox('About the model'):
    st.subheader('Assumptions')
    st.markdown('''
            Number of **DEATH** is the most accurate metric. 
            It will be used to project other metrics under these assumptions for Covid19:  
            The overall case fatality rate: 1 percent  
            Patients need ICU: 5 percent (critical)  
            Patients need hospitalized: 15 percent (severe)  
            Patients with symptom: 20 percent   
            Time to hospitalized since infectected: 13 days (5 days incubation and 8 days from symptom to severe)  
            Time to ICU since hospitalized: 2 days (assume only severe case needs to be hospitalized)  
            Time to death since ICU use: 5 days  
            7 days discharge if not in ICU or coming back from ICU  
            Average ICU time use: 10 (included both dead (5) and alive(11)): (5+11*4)/5  
            Only ICU (critical) patients can develop death  
            ''')
    st.subheader('Projections')
    st.markdown('''
            1. Total number of infection at large: death*100 (not too meaningful) or infected rate in population 
            (for individual and company to quantify risk of infection, for public health dept to declare herd immunity, 
            relax lock down measurements).
            This has a **20 days lag**, ie. this number is of 20 days ago. 
            Only in total lockdown setting, we can use the cummulative death from day 20th times 100 to get 
            total number of infection at large accurately. 
            Other alternative is whole population testing to get this number immediately. 
            2. With a correct forecast on number of death, we can get the forecast for number of hospital beds needed. 
            This is  used to build more hospital beds in advance.
            Each new death equal to 15 hospitalized (5+2)7 days before the death and continue for 10 days
            (using the 15% hospital rate and 1% death rate and 10 days average hospitalized and 
            5 days from ICU to death, 2 days from hospital to ICU)
            3. With a correct forecast number of death, we can get the forecast for number of ICU needed. 
            This is used to prepare ICU and buying ventilators or prepare for hospital white flags moment, 
            when doctors have to decide who to treat and who left to death due to constraint on ICU, ventilator. 
            This is also needed to prepare for social unrest.
            Each new death equal to 5 ICU beds 5 days before the death and continue for 10 days 
            (using the 5% ICU rate and 1% death rate and 10 days average ICU used)
            ''')
    st.subheader('Forecasting death')
    st.markdown('''
    Since this is highly contagious disease, daily new death, which is a proxy for daily new infected cases
    is modeled as $d(t)=a*d(t-1)$ or equivalent to $d(t) = b*a^t$.   
    After a log transform, it becomes linear: $log(d(t))=logb+t*loga$ , so we can use linear regression to 
    provide forecast.   
    We actually use robust linear regressor to avoid data anomaly in death reporting.  
    There are two seperate linear curves, one before the lockdown is effective (21 days after lockdown) and one after.
    For using this prediction to infer back the other metrics (infected cases, hospital, ICU, etc..) only the before
    curve is used and valid. If we assume there is no new infection after lock down (perfect lockdown), the after
    curve only depends on the distribution of time to death since ICU. Since this is unknown, we have to fit the second
    curve. So for this piecewise linear function, we use package 
    [pwlf](https://jekel.me/piecewise_linear_fit_py/index.html#) with breakpoints set at lockdown effective date.
    
    
    WARNING: if lockdown_date is not provided, we will default to no lockdown to raise awareness of worst case
    if no action. If you have info on lock down date please use it to make sure the model provide accurate result
            ''')
    st.subheader('Implications')
    st.markdown('''
            Implications are observed in data everywhere:  
            
            
            0. ***Do not use only confirmed case to make decision***. It is misleading and distorted by testing capicity
            1. Country with severe testing constraint will see death rate lurking around 10-15%, 
            which is 1% death/15%hospitalized. E.g. Italy, Spain, Iran at the beginning. 
            While country with enough testing for all symptomatic patients see rate less than 5% (1%/20%).
            And country that can test most of potential patients, through contact tracing like South Korea and Germany,
            can get closer to 1%. It is very hard to get under 1% unless an effective cure is in hand. Maybe Vietnam?   
            2. After lock down, we need at least 15 days to see daily new cases peaks and around 20 days to see daily 
            new deaths peak, which is just in the most effective lock down. 
            For a less successful one, or severe limit on testing, this number of lag day is higher on new cases and 
            deaths.           
            3. The death peak is about 5 days after the cases peak, but cases depends on testing.   
            4. It needs about a month from the peak for new cases completely dissipate. 
            The number of death is also slow down but have a fat tail and a about 20 days longer than the cases tail.            
            5. The above does not apply to country using widespread testing in place of SIP/lockdown like Korea.            
            6. When no ICU, ventilator available, death rate can increase at most 5 times
            ''')
    st.subheader('TODO')
    st.markdown('''
            1. Need to understand how long since infection, patient is no longer a source of infection to forecast
            curve after lock down period relaxed.          
            2. Upgrade the calculation using mean to use distribution if enough data is available.''')
if st.checkbox('Medical myths'):
    st.markdown('I am not a medical doctor. I am a statistician but I strongly believe in this:')
    st.subheader('How Vietnamese doctors treat SARS before and COVID19 now?')
    st.markdown('''
    The doctors open all doors and windows to let sunlight in and sick air out. Patients with mild symptom are suggested
    to [gargling with salt water.]
    (https://www.webmd.com/cold-and-flu/features/does-gargling-wlth-salt-water-ease-a-sore-throat#1) 
    Some rare severe patients need treatment, ventilator and/or ECMO anyway. We have no other secrete weapon beside the
    hot humid weather. By doing that, we get very low death rate, zero for now, and low infection rate for doctors. Why
    does it work? We think utmostly, this is an ***airborne*** disease. People got infected or death because of the air 
    they breath in, or more precisely by how much viruses in the air they put into their lungs at that particular 
    moment.''')
    st.subheader('How does patient die from COVID-19?')
    st.markdown('''
    Short answer: not because of the virus but because of their own immune system, particularly the cytokine release 
    syndrome. 
    
    Long answer: When patient got infected, virus can be everywhere from their respiratory tracts, blood, stool,.. 
    but the critical center is in their tonsils. When the density of virus is enough, around 5-14 days after infection, 
    patients start to get a lot of dry cough, which release the virus to the air and to their lungs. 
    And then the lungs cells die very fast due to the immune system rush in and kill everything, the viruses and the
    lung cells). Hence, the disease is named severe acute respiratory syndrome (SARS). How to prevent the death happen?
    Keep patient's lung way from the viruses in the air. And as soon as you can.''')
    st.subheader('Why ventilator is so important? or not?')
    st.markdown('''
    - When lots of lung cells die, the air sacs of the lungs become filled with a gummy yellow fluid, 
    other organs got cut off from the oxygen in blood, and dying too.
    Among those who are critically ill, profound acute hypoxemic respiratory failure from ARDS is the dominant finding.
    The need for mechanical ventilation in those who are critically ill is high ranging from 42 to 100 percent. [Link]
    (https://www.uptodate.com/contents/coronavirus-disease-2019-covid-19-critical-care-issues)  
    - But the ventilator also serves a very important purpose: keep the virus away from the air patient breathes in. So if 
    your local does not have any ventilator left, you can make a cheap breathing device that can filter virus from the 
    air intake and fan away air out of patient. Like open door with big fan. Try to not let patient bubble in their 
    own viruses, just as the patients died in the [adult care facility]
    (https://abc7news.com/health/6-dead-53-infected-with-covid-19-at-hayward-assisted-living-facility/6088815/)''')
    st.subheader('How to be in the 95 percent patients that are not in critical condition?')
    st.markdown('''
    When you are positive for COVID19 but not have enough symptoms to be admitted to hospital, keep your place well 
    ventilated, well lit with sun light, and warmer than normal. Gargle with salt water at least 3 times a day or when
    you want to cough. Try to cough as less as you can using any method you know, or go outside if you need to. And then
    watch your vitals, temperature and blood oxygen level for sign that you can be admitted to hospital for proper care.
    ''')
    st.subheader('How to prevent the transmission?')
    st.markdown('''
    The main thing this website show is that lockdown actually working. So follow the lock down guideline, particularly 
    avoid close air spaces with lots of people, such as airplane, subway, church, etc.., and ***wear mask***.''')

if st.checkbox('References'):
    st.markdown('https://www.uptodate.com/contents/coronavirus-disease-2019-covid-19?source=history_widget')
    st.markdown('https://covid19.healthdata.org Reason we speed up our development. Lots of thing to like. One thing '
                'we would do differently, the forecasting model.')
    st.markdown('https://www.streamlit.io Fast prototype.')