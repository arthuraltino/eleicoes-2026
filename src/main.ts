import { mount } from 'svelte';
import './app.css';
import App from './components/App.svelte';

mount(App, { target: document.getElementById('app')! });
