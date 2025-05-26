import axios from 'axios';

axios.defaults.baseURL = 'http://localhost:8000';
axios.defaults.headers.common['X-API-KEY'] = 'Wmx@20020413';

export default axios;
