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
  Rocket,
  Sparkle,
  Globe,
  Award
} from 'lucide-react'
import { motion } from 'framer-motion'

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
      <main className="min-h-screen flex items-center justify-center bg-white">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-turquoise-500"></div>
      </main>
    )
  }

  return (
    <div className="min-h-screen bg-white text-neutral-900 selection:bg-brand-turquoise-100 selection:text-brand-turquoise-900">
      {/* Navigation */}
      <nav className="fixed top-0 w-full glass z-50 border-b border-neutral-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-3 group cursor-pointer">
              <div className="w-10 h-10 bg-gradient-to-br from-brand-turquoise-500 to-brand-turquoise-600 rounded-xl flex items-center justify-center shadow-lg shadow-brand-turquoise-500/20 group-hover:scale-110 transition-transform">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight text-neutral-900">
                JobHunt<span className="text-brand-turquoise-600">Pro</span>
              </span>
            </div>
            
            <div className="hidden md:flex items-center space-x-8">
              <Link href="#features" className="text-neutral-600 hover:text-brand-turquoise-600 transition-colors font-medium text-sm">Features</Link>
              <Link href="#how-it-works" className="text-neutral-600 hover:text-brand-turquoise-600 transition-colors font-medium text-sm">How it works</Link>
              <Link href="#testimonials" className="text-neutral-600 hover:text-brand-turquoise-600 transition-colors font-medium text-sm">Success Stories</Link>
            </div>

            <div className="flex items-center space-x-4">
              <Link href="/auth/login" className="text-neutral-600 hover:text-brand-turquoise-600 transition-colors font-semibold text-sm px-4">
                Sign In
              </Link>
              <Link
                href="/auth/signup"
                className="btn-premium px-6 py-2.5 bg-brand-turquoise-600 text-white rounded-full font-bold text-sm shadow-lg shadow-brand-turquoise-500/20 hover:shadow-brand-turquoise-500/40"
              >
                Get Started Free
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-24 px-4 sm:px-6 lg:px-8 overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-turquoise-50/50 via-white to-white">
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="text-left"
            >
              <div className="inline-flex items-center space-x-2 px-4 py-2 bg-brand-turquoise-50 rounded-full text-xs font-bold text-brand-turquoise-700 mb-6 border border-brand-turquoise-100">
                <Sparkle className="w-3 h-3" />
                <span>AI-POWERED JOB SEARCH ENGINE</span>
              </div>
              
              <h1 className="text-5xl sm:text-6xl lg:text-7xl font-black text-neutral-900 mb-6 leading-[1.1] tracking-tight">
                Land Your <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-turquoise-600 to-brand-orange-500">Dream Job</span> <br />
                Faster Than Ever.
              </h1>
              
              <p className="text-lg text-neutral-600 mb-10 max-w-xl leading-relaxed">
                Stop applying blindly. JobHuntPro uses advanced AI to match your unique skills with the perfect roles and tailors your CV automatically for every application.
              </p>

              <div className="flex flex-wrap gap-4">
                <Link
                  href="/auth/signup"
                  className="btn-premium px-8 py-4 bg-brand-turquoise-600 text-white rounded-2xl font-bold text-lg flex items-center space-x-3 group"
                >
                  <span>Start My Career Journey</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  href="#features"
                  className="px-8 py-4 bg-white border-2 border-neutral-100 text-neutral-700 rounded-2xl font-bold text-lg hover:border-brand-turquoise-200 transition-all"
                >
                  Explore Features
                </Link>
              </div>

              <div className="mt-10 flex items-center space-x-6 text-neutral-500">
                <div className="flex -space-x-3">
                  {[1,2,3,4].map(i => (
                    <div key={i} className="w-10 h-10 rounded-full border-2 border-white bg-neutral-100 flex items-center justify-center overflow-hidden">
                      <img src={`https://i.pravatar.cc/150?u=${i}`} alt="user" />
                    </div>
                  ))}
                </div>
                <div className="text-sm">
                  <p className="font-bold text-neutral-900">12k+ Users</p>
                  <p>Trust JobHuntPro</p>
                </div>
                <div className="h-8 w-px bg-neutral-200"></div>
                <div className="flex items-center space-x-1">
                  <Star className="w-4 h-4 text-brand-orange-500 fill-brand-orange-500" />
                  <span className="font-bold text-neutral-900">4.9/5</span>
                  <span className="text-xs">Trustpilot</span>
                </div>
              </div>
            </motion.div>

            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1 }}
              className="relative"
            >
              <div className="relative z-10 glass rounded-[2.5rem] p-4 shadow-2xl border border-white">
                <div className="bg-neutral-900 rounded-[2rem] overflow-hidden aspect-[4/3] relative">
                  <div className="absolute inset-0 bg-gradient-to-tr from-brand-turquoise-500/20 to-brand-orange-500/20"></div>
                  <div className="p-8 h-full flex flex-col justify-center items-center text-center">
                    <div className="w-20 h-20 bg-brand-turquoise-500 rounded-2xl flex items-center justify-center mb-6 shadow-xl">
                      <Brain className="w-10 h-10 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-2">Analyzing 50k+ Jobs...</h3>
                    <p className="text-neutral-400 text-sm mb-6">Finding your perfect match based on 42 skills</p>
                    <div className="w-full max-w-xs bg-neutral-800 h-2 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: '85%' }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="h-full bg-brand-turquoise-500"
                      />
                    </div>
                  </div>
                </div>
              </div>
              {/* Decorative elements */}
              <div className="absolute -top-10 -right-10 w-40 h-40 bg-brand-orange-200 rounded-full blur-3xl opacity-30 animate-pulse"></div>
              <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-brand-turquoise-200 rounded-full blur-3xl opacity-30 animate-pulse delay-700"></div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-neutral-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-20">
            <h2 className="text-4xl font-black text-neutral-900 mb-6">Features Built for Conversion</h2>
            <p className="text-neutral-600 text-lg">We've automated the tedious parts of the job hunt so you can focus on the interviews.</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                icon: Target,
                title: "Precision Matching",
                desc: "Our AI doesn't just look at keywords; it understands your career trajectory and intent.",
                color: "brand-turquoise"
              },
              {
                icon: Wand2,
                title: "Automatic CV Tailoring",
                desc: "Generate a custom, ATS-optimized CV for every single job with one click.",
                color: "brand-orange"
              },
              {
                icon: Rocket,
                title: "One-Click Apply",
                desc: "Integrated application tracking and cover letter generation to 10x your output.",
                color: "brand-turquoise"
              }
            ].map((feature, idx) => (
              <div key={idx} className="bg-white p-10 rounded-[2rem] shadow-sm border border-neutral-100 hover:shadow-xl hover:border-brand-turquoise-100 transition-all group">
                <div className={`w-14 h-14 bg-${feature.color}-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                  <feature.icon className={`w-7 h-7 text-${feature.color}-600`} />
                </div>
                <h3 className="text-xl font-bold text-neutral-900 mb-4">{feature.title}</h3>
                <p className="text-neutral-500 leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof / Trust */}
      <section className="py-20 border-y border-neutral-100">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-sm font-bold text-neutral-400 uppercase tracking-widest mb-10">Our Users Work At</p>
          <div className="flex flex-wrap justify-center items-center gap-12 md:gap-20 grayscale opacity-40">
            <h2 className="text-2xl font-black italic">Google</h2>
            <h2 className="text-2xl font-black italic">Amazon</h2>
            <h2 className="text-2xl font-black italic">Meta</h2>
            <h2 className="text-2xl font-black italic">Microsoft</h2>
            <h2 className="text-2xl font-black italic">Apple</h2>
          </div>
        </div>
      </section>

      {/* Modern Dashboard Preview / Value Prop */}
      <section className="py-24 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-neutral-900 rounded-[3rem] p-12 md:p-20 relative overflow-hidden shadow-2xl">
            <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-brand-turquoise-500/10 to-transparent"></div>
            <div className="grid md:grid-cols-2 gap-16 items-center relative z-10">
              <div>
                <h2 className="text-4xl md:text-5xl font-black text-white mb-8 leading-tight">
                  A Dashboard That <br />
                  <span className="text-brand-turquoise-400">Works For You.</span>
                </h2>
                <ul className="space-y-6">
                  {[
                    "Real-time market insights for your job title",
                    "Success probability score for every match",
                    "Automated application tracking",
                    "Direct feedback from AI on CV improvements"
                  ].map((item, i) => (
                    <li key={i} className="flex items-center space-x-4 text-neutral-300">
                      <div className="w-6 h-6 rounded-full bg-brand-turquoise-500/20 flex items-center justify-center">
                        <CheckCircle2 className="w-4 h-4 text-brand-turquoise-400" />
                      </div>
                      <span className="text-lg">{item}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-12">
                  <Link href="/auth/signup" className="btn-premium inline-flex items-center space-x-3 px-8 py-4 bg-brand-orange-500 text-white rounded-2xl font-bold">
                    <span>Explore Dashboard</span>
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                </div>
              </div>
              <div className="relative">
                <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl">
                   <div className="space-y-4">
                      {[1, 2, 3].map(i => (
                        <div key={i} className="h-16 bg-white/5 rounded-xl border border-white/5 flex items-center px-6 justify-between">
                          <div className="flex items-center space-x-4">
                            <div className="w-10 h-10 bg-brand-turquoise-500/20 rounded-lg"></div>
                            <div className="space-y-1">
                              <div className="h-2 w-24 bg-white/20 rounded"></div>
                              <div className="h-2 w-16 bg-white/10 rounded"></div>
                            </div>
                          </div>
                          <div className="h-2 w-12 bg-brand-orange-500/40 rounded"></div>
                        </div>
                      ))}
                   </div>
                </div>
                <div className="absolute -bottom-6 -right-6 glass p-6 rounded-2xl shadow-2xl border border-white/10">
                  <p className="text-white font-bold text-2xl">98%</p>
                  <p className="text-white/60 text-xs">Match Accuracy</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <Award className="w-12 h-12 text-brand-orange-500 mb-6" />
              <h2 className="text-4xl font-black mb-8 leading-tight italic">
                "JobHuntPro didn't just find me a job; they found me the right career path. The AI CV tailoring is pure magic."
              </h2>
              <div>
                <p className="font-bold text-xl">Sarah Jenkins</p>
                <p className="text-neutral-500">Software Engineer at Meta</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div className="bg-neutral-50 p-8 rounded-3xl mt-12">
                <p className="text-4xl font-black text-brand-turquoise-600 mb-2">3x</p>
                <p className="text-sm font-bold text-neutral-600 uppercase">Interview Rate</p>
              </div>
              <div className="bg-neutral-50 p-8 rounded-3xl">
                <p className="text-4xl font-black text-brand-orange-500 mb-2">10hrs</p>
                <p className="text-sm font-bold text-neutral-600 uppercase">Saved Weekly</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Final */}
      <section className="py-32 bg-brand-turquoise-600 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
        <div className="max-w-4xl mx-auto px-4 text-center relative z-10">
          <h2 className="text-5xl md:text-6xl font-black text-white mb-10 leading-tight">Ready to transform <br /> your career?</h2>
          <div className="flex flex-col sm:flex-row justify-center items-center gap-6">
            <Link href="/auth/signup" className="w-full sm:w-auto px-12 py-5 bg-white text-brand-turquoise-700 rounded-2xl font-black text-xl hover:bg-neutral-50 shadow-2xl transition-all active:scale-95">
              Get Started Now - It's Free
            </Link>
          </div>
          <p className="text-white/80 mt-10 font-medium">No credit card required. Cancel anytime.</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-20 bg-white border-t border-neutral-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-12">
            <div className="col-span-1 md:col-span-1">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-8 h-8 bg-brand-turquoise-500 rounded-lg flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <span className="text-lg font-bold">JobHuntPro</span>
              </div>
              <p className="text-neutral-500 text-sm leading-relaxed">
                The AI-powered command center for your next career move. Built for high-performers.
              </p>
            </div>
            
            <div>
              <h4 className="font-bold text-sm uppercase tracking-widest text-neutral-400 mb-6">Product</h4>
              <ul className="space-y-4 text-neutral-600 font-medium text-sm">
                <li><Link href="#features" className="hover:text-brand-turquoise-600">Features</Link></li>
                <li><Link href="#how-it-works" className="hover:text-brand-turquoise-600">Algorithm</Link></li>
                <li><Link href="#" className="hover:text-brand-turquoise-600">CV Builder</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-widest text-neutral-400 mb-6">Resources</h4>
              <ul className="space-y-4 text-neutral-600 font-medium text-sm">
                <li><Link href="#" className="hover:text-brand-turquoise-600">Career Blog</Link></li>
                <li><Link href="#" className="hover:text-brand-turquoise-600">Resume Tips</Link></li>
                <li><Link href="#" className="hover:text-brand-turquoise-600">Salary Guide</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="font-bold text-sm uppercase tracking-widest text-neutral-400 mb-6">Support</h4>
              <ul className="space-y-4 text-neutral-600 font-medium text-sm">
                <li><Link href="#" className="hover:text-brand-turquoise-600">Help Center</Link></li>
                <li><Link href="#" className="hover:text-brand-turquoise-600">Privacy Policy</Link></li>
                <li><Link href="#" className="hover:text-brand-turquoise-600">Terms of Service</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-20 pt-8 border-t border-neutral-100 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="text-neutral-400 text-sm">&copy; {new Date().getFullYear()} JobHuntPro. All rights reserved.</p>
            <div className="flex items-center space-x-6">
              <Link href="#" className="text-neutral-400 hover:text-brand-turquoise-600"><Globe className="w-5 h-5" /></Link>
              <Link href="#" className="text-neutral-400 hover:text-brand-turquoise-600"><Users className="w-5 h-5" /></Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
