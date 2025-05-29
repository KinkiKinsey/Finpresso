import axios from 'axios';

axios.defaults.baseURL = 'http://www.fintegrateai.com:8000';
axios.defaults.headers.common['X-API-KEY'] = 'Wmx@20020413';

export default axios;
