import { motion } from 'motion/react';

import { Button } from '../ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card';
import { MODULES } from '../../content/siteContent';
import { fadeInUp, staggerContainer } from './animations';

export function ModulesSection() {
  return (
    <section id="modules" className="px-4 py-20">
      <div className="mx-auto max-w-7xl">
        <motion.div
          className="mb-12 text-center"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeInUp}
          transition={{ duration: 0.5 }}
        >
          <h2 className="mb-4 text-4xl text-gray-900">Moduły Magento 2</h2>
          <p className="text-xl text-gray-600">
            Profesjonalne rozszerzenia dostępne w modelu subskrypcji
          </p>
        </motion.div>

        <motion.div
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
          variants={staggerContainer}
        >
          {MODULES.map((module) => {
            const Icon = module.icon;

            return (
              <motion.div key={module.title} variants={fadeInUp}>
                <Card className="transition-shadow hover:shadow-lg">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="mb-2">{module.title}</CardTitle>
                        <CardDescription>{module.description}</CardDescription>
                      </div>
                      <Icon className="text-blue-600" size={24} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-gray-600">
                      {module.features.map((feature) => (
                        <li key={feature}>• {feature}</li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </motion.div>

        <div className="mt-12 text-center">
          <p className="mb-4 text-gray-600">
            Wkrótce dostępne w formie subskrypcji
          </p>
          <Button
            size="lg"
            className="bg-blue-600 text-white hover:bg-blue-700"
          >
            Zapisz się na listę oczekujących
          </Button>
        </div>
      </div>
    </section>
  );
}
