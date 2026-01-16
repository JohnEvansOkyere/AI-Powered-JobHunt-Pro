'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import Link from 'next/link'
import { 
  Sparkles, 
  Target, 
  Zap, 
  Shield, 
  TrendingUp, 
  CheckCircle2,
  ArrowRight,
  Star,
  Users,
  Briefcase,
  FileText,
  Search,
  Wand2,
  Brain,
  Globe,
  Lock,
  Rocket,
  Sparkle
} from 'lucide-react'

export default function HomePage() {
  const { isAuthenticated, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, loading, router])

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-neutral-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </main>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-900 text-neutral-100">
      {/* Navigation */}
      <nav className="fixed top-0 w-full glass z-50 border-b border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-3">
              <div className="w-11 h-11 bg-gradient-to-br from-primary-500 via-secondary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg shadow-primary-500/20">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold gradient-text">
                Veloxa Smart Match
              </span>
            </div>
            <div className="hidden md:flex items-center space-x-10">
              <Link href="#features" className="text-neutral-400 hover:text-primary-400 transition-colors font-medium">
                Features
              </Link>
              <Link href="#how-it-works" className="text-neutral-400 hover:text-primary-400 transition-colors font-medium">
                How It Works
              </Link>
              <Link href="#benefits" className="text-neutral-400 hover:text-primary-400 transition-colors font-medium">
                Benefits
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/auth/login"
                className="text-neutral-300 hover:text-white transition-colors font-medium px-4 py-2"
              >
                Sign In
              </Link>
              <Link
                href="/auth/signup"
                className="group px-6 py-3 bg-gradient-to-r from-primary-600 via-secondary-600 to-accent-600 text-white rounded-xl font-semibold hover:shadow-2xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-0.5 flex items-center space-x-2"
              >
                <span>Get Started Free</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-32 px-4 sm:px-6 lg:px-8 overflow-hidden">
        {/* Animated gradient background */}
        <div className="absolute inset-0 gradient-animated opacity-10"></div>
        
        {/* Floating orbs */}
        <div className="absolute top-20 left-10 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl animate-blob"></div>
        <div className="absolute top-40 right-20 w-96 h-96 bg-secondary-500/20 rounded-full blur-3xl animate-blob animation-delay-2000"></div>
        <div className="absolute bottom-20 left-1/2 w-96 h-96 bg-accent-500/20 rounded-full blur-3xl animate-blob animation-delay-4000"></div>

        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center max-w-5xl mx-auto">
            {/* Badge */}
            <div className="inline-flex items-center space-x-2 px-5 py-2.5 glass rounded-full text-sm font-semibold mb-8 animate-fade-in border border-primary-500/30">
              <Sparkle className="w-4 h-4 text-primary-400" />
              <span className="text-primary-300">100% Free Forever</span>
              <span className="text-neutral-400">•</span>
              <span className="text-neutral-300">No Credit Card Required</span>
            </div>

            {/* Main Heading */}
            <h1 className="text-6xl sm:text-7xl lg:text-8xl font-extrabold mb-8 animate-slide-up leading-tight">
              <span className="block mb-2">Find Your</span>
              <span className="gradient-text block">Dream Job</span>
              <span className="block mt-2 text-neutral-300">with AI-Powered Matching</span>
            </h1>

            {/* Subheading */}
            <p className="text-xl sm:text-2xl text-neutral-400 mb-12 max-w-3xl mx-auto leading-relaxed animate-slide-up animation-delay-200">
              Smart job matching that analyzes your skills, experience, and career goals. 
              Get personalized job recommendations and tailor your CV to each match—all powered by AI.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-5 justify-center items-center mb-20 animate-slide-up animation-delay-400">
              <Link
                href="/auth/signup"
                className="group relative px-8 py-4 bg-gradient-to-r from-primary-600 via-secondary-600 to-accent-600 text-white rounded-2xl font-bold text-lg hover:shadow-2xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-1 flex items-center space-x-3 overflow-hidden"
              >
                <span className="relative z-10">Start Matching Now</span>
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform relative z-10" />
                <div className="absolute inset-0 bg-gradient-to-r from-primary-500 via-secondary-500 to-accent-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </Link>
              <Link
                href="#how-it-works"
                className="px-8 py-4 glass border-2 border-neutral-700 text-neutral-200 rounded-2xl font-semibold text-lg hover:border-primary-500 hover:text-primary-400 transition-all shadow-lg"
              >
                See How It Works
              </Link>
            </div>

            {/* Trust Indicators */}
            <div className="flex flex-wrap justify-center items-center gap-10 text-neutral-400 animate-fade-in animation-delay-600">
              <div className="flex items-center space-x-2.5">
                <Users className="w-5 h-5 text-primary-400" />
                <span className="font-semibold text-neutral-300">10,000+ Active Users</span>
              </div>
              <div className="flex items-center space-x-2.5">
                <Briefcase className="w-5 h-5 text-secondary-400" />
                <span className="font-semibold text-neutral-300">50,000+ Job Matches</span>
              </div>
              <div className="flex items-center space-x-2.5">
                <Star className="w-5 h-5 text-accent-400" />
                <span className="font-semibold text-neutral-300">4.9/5 Rating</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section - Modern Style */}
      <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-neutral-950 relative">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-5xl sm:text-6xl font-extrabold mb-6">
              <span className="gradient-text">Powerful Features</span>
              <span className="text-neutral-200"> for Your Career</span>
            </h2>
            <p className="text-xl text-neutral-400 max-w-2xl mx-auto">
              Everything you need to find and land your perfect job, all in one place
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: 'AI Job Matching',
                description: 'Advanced AI algorithms analyze thousands of jobs daily and match you with opportunities that perfectly align with your skills, experience, and career goals.',
                gradient: 'from-primary-500/20 via-primary-500/10 to-transparent',
                borderGradient: 'border-primary-500/30',
                iconGradient: 'from-primary-500 to-primary-600',
              },
              {
                icon: Wand2,
                title: 'Smart CV Tailoring',
                description: 'Upload your CV once, then click "Generate CV" for any job match. Our AI automatically tailors your CV to highlight the most relevant skills and experiences for each position.',
                gradient: 'from-secondary-500/20 via-secondary-500/10 to-transparent',
                borderGradient: 'border-secondary-500/30',
                iconGradient: 'from-secondary-500 to-secondary-600',
              },
              {
                icon: Zap,
                title: 'Instant Applications',
                description: 'Generate tailored cover letters and application materials in seconds. No more spending hours crafting each application—let AI do the heavy lifting.',
                gradient: 'from-accent-500/20 via-accent-500/10 to-transparent',
                borderGradient: 'border-accent-500/30',
                iconGradient: 'from-accent-500 to-accent-600',
              },
              {
                icon: Search,
                title: 'Smart Job Search',
                description: 'Browse thousands of curated tech jobs from multiple sources, updated daily. Filter by location, salary, remote options, and more.',
                gradient: 'from-primary-500/20 via-primary-500/10 to-transparent',
                borderGradient: 'border-primary-500/30',
                iconGradient: 'from-primary-500 to-primary-600',
              },
              {
                icon: FileText,
                title: 'Professional CV Builder',
                description: 'Create ATS-friendly resumes and CVs that pass through applicant tracking systems. Our builder ensures your CV gets noticed by recruiters.',
                gradient: 'from-secondary-500/20 via-secondary-500/10 to-transparent',
                borderGradient: 'border-secondary-500/30',
                iconGradient: 'from-secondary-500 to-secondary-600',
              },
              {
                icon: TrendingUp,
                title: 'Career Insights',
                description: 'Track your applications, match quality scores, and get actionable insights to improve your success rate. See what\'s working and optimize your approach.',
                gradient: 'from-accent-500/20 via-accent-500/10 to-transparent',
                borderGradient: 'border-accent-500/30',
                iconGradient: 'from-accent-500 to-accent-600',
              },
            ].map((feature, index) => (
              <div
                key={index}
                className="group relative p-8 glass rounded-2xl border border-neutral-800 hover:border-transparent transition-all transform hover:-translate-y-2 hover:shadow-2xl overflow-hidden"
              >
                {/* Gradient background on hover */}
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}></div>
                
                {/* Animated border on hover */}
                <div className={`absolute inset-0 rounded-2xl border-2 ${feature.borderGradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}></div>
                
                <div className="relative z-10">
                  <div className={`w-16 h-16 bg-gradient-to-br ${feature.iconGradient} rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg`}>
                    <feature.icon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-neutral-100 mb-4 group-hover:text-white transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-neutral-400 leading-relaxed group-hover:text-neutral-300 transition-colors">
                    {feature.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 px-4 sm:px-6 lg:px-8 bg-neutral-900 relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary-500/5 to-transparent"></div>
        
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-20">
            <h2 className="text-5xl sm:text-6xl font-extrabold mb-6">
              <span className="text-neutral-200">How It</span>
              <span className="gradient-text"> Works</span>
            </h2>
            <p className="text-xl text-neutral-400 max-w-2xl mx-auto">
              Get started in minutes and find your perfect job match
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-12 relative">
            {/* Connecting line for desktop */}
            <div className="hidden md:block absolute top-24 left-1/4 right-1/4 h-0.5 bg-gradient-to-r from-transparent via-primary-500 to-transparent"></div>

            {[
              {
                step: '1',
                title: 'Create Your Profile',
                description: 'Sign up for free and build your professional profile with skills, experience, and preferences. Upload your CV to get started.',
                icon: Rocket,
              },
              {
                step: '2',
                title: 'AI Matches Jobs',
                description: 'Our AI analyzes thousands of jobs daily and matches you with opportunities that fit perfectly. Get personalized recommendations instantly.',
                icon: Brain,
              },
              {
                step: '3',
                title: 'Tailor & Apply',
                description: 'Click "Generate CV" for any job match to get a tailored version of your CV. Then generate personalized cover letters and apply with confidence.',
                icon: Sparkles,
              },
            ].map((step, index) => (
              <div key={index} className="relative text-center">
                <div className="w-24 h-24 bg-gradient-to-br from-primary-600 via-secondary-600 to-accent-600 rounded-2xl flex items-center justify-center text-white text-3xl font-bold mx-auto mb-8 relative z-10 shadow-2xl shadow-primary-500/30 transform hover:scale-110 transition-transform">
                  <step.icon className="w-12 h-12" />
                </div>
                <div className="glass rounded-2xl p-8 border border-neutral-800 hover:border-primary-500/50 transition-all">
                  <h3 className="text-2xl font-bold text-neutral-100 mb-4">
                    {step.title}
                  </h3>
                  <p className="text-neutral-400 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="benefits" className="py-24 px-4 sm:px-6 lg:px-8 bg-neutral-950 relative">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-5xl sm:text-6xl font-extrabold mb-8">
                <span className="text-neutral-200">Why Choose</span>
                <br />
                <span className="gradient-text">Veloxa Smart Match?</span>
              </h2>
              <p className="text-xl text-neutral-400 mb-10 leading-relaxed">
                Join the future of job searching with AI-powered tools designed for your success. 
                Every feature is built to help you land your dream job faster.
              </p>
              <div className="space-y-5">
                {[
                  '100% Free Forever - No hidden fees or subscriptions',
                  'Save 10+ hours per week on job applications',
                  '3x higher interview rate with tailored CVs',
                  'Real-time job matching from multiple sources',
                  'AI-powered CV tailoring to each job match',
                  'Privacy-focused - your data stays secure',
                ].map((benefit, index) => (
                  <div key={index} className="flex items-start space-x-4 group">
                    <div className="w-6 h-6 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 group-hover:scale-110 transition-transform">
                      <CheckCircle2 className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-lg text-neutral-300 group-hover:text-white transition-colors">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <div className="glass rounded-3xl p-8 border border-neutral-800 shadow-2xl">
                <div className="space-y-6">
                  {[
                    { label: 'Time Saved', value: '10hrs', sub: 'Per Application', gradient: 'from-primary-500 to-primary-600' },
                    { label: 'Match Accuracy', value: '95%', sub: 'AI-Powered', gradient: 'from-secondary-500 to-secondary-600' },
                    { label: 'Success Rate', value: '3x', sub: 'Interview Rate', gradient: 'from-accent-500 to-accent-600' },
                  ].map((stat, index) => (
                    <div key={index} className={`p-6 bg-gradient-to-br ${stat.gradient} rounded-2xl shadow-lg transform hover:scale-105 transition-transform`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-bold text-white/90 text-sm mb-1">{stat.label}</p>
                          <p className="text-white/70 text-xs">{stat.sub}</p>
                        </div>
                        <div className="text-4xl font-extrabold text-white">{stat.value}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Floating decoration */}
              <div className="absolute -top-6 -right-6 w-24 h-24 bg-primary-500/20 rounded-full blur-2xl animate-float"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-32 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
        <div className="absolute inset-0 gradient-animated opacity-20"></div>
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="text-5xl sm:text-6xl font-extrabold text-white mb-8">
            Ready to Find Your Dream Job?
          </h2>
          <p className="text-xl text-neutral-300 mb-12 max-w-2xl mx-auto leading-relaxed">
            Join thousands of professionals who are already using Veloxa Smart Match to advance their careers. 
            Start your free journey today.
          </p>
          <Link
            href="/auth/signup"
            className="inline-flex items-center space-x-3 px-10 py-5 bg-gradient-to-r from-primary-600 via-secondary-600 to-accent-600 text-white rounded-2xl font-bold text-lg hover:shadow-2xl hover:shadow-primary-500/50 transition-all transform hover:-translate-y-1"
          >
            <span>Get Started Free</span>
            <ArrowRight className="w-6 h-6" />
          </Link>
          <p className="text-neutral-400 text-sm mt-8">
            No credit card required • Set up in 2 minutes • Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-16 px-4 sm:px-6 lg:px-8 bg-neutral-950 border-t border-neutral-800">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 via-secondary-500 to-accent-500 rounded-xl flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-white" />
                </div>
                <span className="text-lg font-bold text-white">Veloxa Smart Match</span>
              </div>
              <p className="text-sm text-neutral-400 leading-relaxed">
                AI-powered job matching platform helping professionals find their dream careers.
              </p>
            </div>
            <div>
              <h4 className="font-bold text-white mb-4">Product</h4>
              <ul className="space-y-3 text-sm text-neutral-400">
                <li><Link href="#features" className="hover:text-primary-400 transition-colors">Features</Link></li>
                <li><Link href="#how-it-works" className="hover:text-primary-400 transition-colors">How It Works</Link></li>
                <li><Link href="#benefits" className="hover:text-primary-400 transition-colors">Benefits</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-white mb-4">Company</h4>
              <ul className="space-y-3 text-sm text-neutral-400">
                <li><Link href="https://veloxarecruit.com" target="_blank" className="hover:text-primary-400 transition-colors">About Veloxa</Link></li>
                <li><a href="#" className="hover:text-primary-400 transition-colors">Contact</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-white mb-4">Legal</h4>
              <ul className="space-y-3 text-sm text-neutral-400">
                <li><a href="#" className="hover:text-primary-400 transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-primary-400 transition-colors">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-neutral-800 pt-8 text-center text-sm text-neutral-500">
            <p>&copy; {new Date().getFullYear()} Veloxa Smart Match. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
