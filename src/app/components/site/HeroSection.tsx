import { motion } from 'motion/react';

import { Button } from '../ui/button';
import { fadeInUp } from './animations';

type HeroSectionProps = {
  onExploreServices: () => void;
};

export function HeroSection({ onExploreServices }: HeroSectionProps) {
  return (
    <section id="home" className="px-4 pb-20 pt-32">
      <motion.div
        className="mx-auto max-w-7xl text-center"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
        variants={fadeInUp}
        transition={{ duration: 0.6 }}
      >
        <h1 className="mb-6 text-5xl text-gray-900 md:text-6xl">
          Gama Software
        </h1>
        <p className="mx-auto mb-8 max-w-3xl text-xl text-gray-600 md:text-2xl">
          Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz
          budowaniu agentów AI dla Twojego biznesu
        </p>
        <Button
          size="lg"
          onClick={onExploreServices}
          className="bg-blue-600 px-8 py-6 text-lg text-white hover:bg-blue-700"
        >
          Poznaj nasze usługi
        </Button>
      </motion.div>
    </section>
  );
}
