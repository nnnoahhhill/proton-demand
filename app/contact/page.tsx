"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { GlowButton } from "@/components/ui/glow-button";
import { Spinner } from "@/components/ui/spinner";

// Form validation schema
const contactFormSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }),
  email: z.string().email({ message: "Please enter a valid email address." }),
  subject: z.string().min(5, { message: "Subject must be at least 5 characters." }),
  message: z.string().min(10, { message: "Message must be at least 10 characters." }),
});

type ContactFormValues = z.infer<typeof contactFormSchema>;

export default function ContactPage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const form = useForm<ContactFormValues>({
    resolver: zodResolver(contactFormSchema),
    defaultValues: {
      name: "",
      email: "",
      subject: "",
      message: "",
    },
  });

  async function onSubmit(data: ContactFormValues) {
    setIsSubmitting(true);
    setErrorMessage(null);
    
    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to send message");
      }
      
      setSubmitSuccess(true);
      form.reset();

      // Optional: Add analytics tracking here
      console.log("Contact form submitted successfully");
    } catch (error) {
      console.error("Error sending contact form:", error);
      setErrorMessage(
        error instanceof Error ? error.message : "An unknown error occurred"
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="container px-4 py-12 max-w-4xl mx-auto">
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-3xl font-andale">Contact Us</h1>
          <p className="text-white/70 font-avenir">
            Have questions or need a custom quote? Fill out the form below and we'll get back to you as soon as possible.
          </p>
        </div>

        {submitSuccess ? (
          <div className="border border-[#5fe496] bg-[#5fe496]/10 p-6 rounded-none">
            <h3 className="text-xl font-andale mb-2 text-[#5fe496]">Message Sent!</h3>
            <p className="text-white font-avenir">
              Thank you for contacting us. We'll get back to you as soon as possible.
            </p>
            <GlowButton
              onClick={() => setSubmitSuccess(false)}
              className="mt-4 bg-[#1e87d6] text-white hover:bg-[#1e87d6]/80"
            >
              Send Another Message
            </GlowButton>
          </div>
        ) : (
          <div className="border border-[#1E2A45] bg-[#0C1F3D]/50 p-6 rounded-none">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white/70 font-avenir">Name</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            className="bg-[#0A1525] border border-[#1E2A45] text-white rounded-none"
                            placeholder="Your name"
                          />
                        </FormControl>
                        <FormMessage className="text-[#F46036]" />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-white/70 font-avenir">Email</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            className="bg-[#0A1525] border border-[#1E2A45] text-white rounded-none"
                            placeholder="your.email@example.com"
                          />
                        </FormControl>
                        <FormMessage className="text-[#F46036]" />
                      </FormItem>
                    )}
                  />
                </div>
                <FormField
                  control={form.control}
                  name="subject"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-white/70 font-avenir">Subject</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          className="bg-[#0A1525] border border-[#1E2A45] text-white rounded-none"
                          placeholder="What's this about?"
                        />
                      </FormControl>
                      <FormMessage className="text-[#F46036]" />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="message"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-white/70 font-avenir">Message</FormLabel>
                      <FormControl>
                        <Textarea
                          {...field}
                          className="bg-[#0A1525] border border-[#1E2A45] text-white rounded-none min-h-[120px]"
                          placeholder="Your message"
                        />
                      </FormControl>
                      <FormMessage className="text-[#F46036]" />
                    </FormItem>
                  )}
                />

                {errorMessage && (
                  <div className="text-[#F46036] font-avenir p-3 border border-[#F46036] bg-[#F46036]/10">
                    {errorMessage}
                  </div>
                )}

                <GlowButton
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[#5fe496] text-[#0A1525] hover:bg-[#5fe496]/80 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <div className="flex items-center justify-center">
                      <Spinner size={20} />
                      <span className="ml-2">Sending...</span>
                    </div>
                  ) : (
                    "Send Message"
                  )}
                </GlowButton>
              </form>
            </Form>
          </div>
        )}
      </div>
    </div>
  );
}