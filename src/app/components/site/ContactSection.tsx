import { motion } from 'motion/react';

import { fadeInUp } from './animations';
import { ContactForm } from './ContactForm';

export function ContactSection() {
  return (
    <section id="contact" className="px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <motion.h2
          className="mb-6 text-center text-4xl text-gray-900"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeInUp}
          transition={{ duration: 0.5 }}
        >
          Kontakt
        </motion.h2>

        <motion.div
          className="mx-auto max-w-2xl rounded-lg bg-white p-8 shadow-md md:p-12"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeInUp}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <ContactForm />
        </motion.div>
      </div>
    </section>
  );
}
