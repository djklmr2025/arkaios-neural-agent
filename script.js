import { animate, inView } from "https://esm.run/framer-motion";


document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();


    const sections = document.querySelectorAll('section');
    sections.forEach(section => {
        inView(section, () => {
            animate(
                section,
                { opacity: 1, y: 0 },
                { duration: 0.8, ease: "easeOut" }
            );
        }, { once: true, amount: 0.2 });
    });


    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach((card, index) => {
        inView(card, () => {
            animate(
                card,
                { opacity: 1, y: 0 },
                { duration: 0.5, delay: index * 0.1, ease: "easeOut" }
            );
        }, { once: true, amount: 0.5 });
    });


    const stepCards = document.querySelectorAll('.step-card');
     stepCards.forEach((card, index) => {
        inView(card, () => {
            animate(
                card,
                { opacity: 1, y: 0 },
                { duration: 0.5, delay: index * 0.15, ease: "easeOut" }
            );
        }, { once: true, amount: 0.5 });
    });
    
    const useCaseCards = document.querySelectorAll('.use-case-card');
     useCaseCards.forEach((card, index) => {
        inView(card, () => {
            animate(
                card,
                { opacity: 1, y: 0 },
                { duration: 0.5, delay: index * 0.1, ease: "easeOut" }
            );
        }, { once: true, amount: 0.5 });
    });


    const heroElements = ['#hero h1', '#hero p', '#hero .flex', '#demo-placeholder'];
    heroElements.forEach((selector, index) => {
        animate(
            selector,
            { opacity: [0, 1], y: [20, 0] },
            { duration: 0.7, delay: 0.2 + index * 0.15, ease: 'easeOut' }
        );
    });


});
