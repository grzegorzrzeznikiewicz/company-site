import { motion } from 'motion/react';

import { SERVICES } from '../../content/siteContent';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { fadeInUp, staggerContainer } from './animations';

export function ServicesSection() {
  return (
    <section id="services" className="bg-gray-50 px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <motion.h2
          className="mb-12 text-center text-4xl text-gray-900"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeInUp}
          transition={{ duration: 0.5 }}
        >
          Nasze Usługi
        </motion.h2>

        <motion.div
          className="grid gap-8 md:grid-cols-3"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          variants={staggerContainer}
        >
          {SERVICES.map((service) => {
            const Icon = service.icon;

            return (
              <motion.div key={service.title} variants={fadeInUp} transition={{ duration: 0.5 }}>
                <Card className="border-none shadow-lg transition-shadow hover:shadow-xl">
                  <CardHeader>
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100">
                      <Icon className="text-blue-600" size={24} />
                    </div>
                    <CardTitle>{service.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-base">{service.description}</CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
