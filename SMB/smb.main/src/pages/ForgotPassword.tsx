import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Building2, Mail, Lock, HelpCircle, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<'email' | 'security' | 'password'>('email');
  const [email, setEmail] = useState('');
  const [securityQuestion, setSecurityQuestion] = useState('');
  const [securityAnswer, setSecurityAnswer] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      toast.error('Please enter your email');
      return;
    }

    try {
      const { getSecurityQuestion } = await import('@/services/api');
      const res = await getSecurityQuestion(email);
      if (res && res.securityQuestion) {
        setSecurityQuestion(res.securityQuestion);
        setStep('security');
        toast.success('Security question loaded');
      } else {
        toast.error('Email not found');
      }
    } catch (err: any) {
      toast.error(err?.message || 'Failed to retrieve security question');
    }
  };

  const handleSecuritySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!securityAnswer) {
      toast.error('Please answer the security question');
      return;
    }
    setStep('password');
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPassword || !confirmPassword) {
      toast.error('Please fill in all fields');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    try {
      const { forgotPassword } = await import('@/services/api');
      const res = await forgotPassword({
        email,
        securityAnswer,
        newPassword,
      });
      
      if (res && res.token) {
        // Auto-login after successful password reset
        localStorage.setItem('auth', JSON.stringify({ token: res.token, user: res.user }));
        toast.success('Password reset successfully! You are now logged in.');
        navigate('/dashboard');
      } else {
        toast.error('Password reset failed');
      }
    } catch (err: any) {
      toast.error(err?.message || 'Password reset failed');
    }
  };

  const renderEmailStep = () => (
    <form onSubmit={handleEmailSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email Address</Label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id="email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>
      <Button type="submit" className="w-full gradient-primary text-white">
        Get Security Question
      </Button>
    </form>
  );

  const renderSecurityStep = () => (
    <form onSubmit={handleSecuritySubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="securityQuestion">Security Question</Label>
        <div className="relative">
          <HelpCircle className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id="securityQuestion"
            value={securityQuestion}
            readOnly
            className="pl-10 bg-muted"
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="securityAnswer">Your Answer</Label>
        <div className="relative">
          <Shield className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id="securityAnswer"
            placeholder="Enter your answer"
            value={securityAnswer}
            onChange={(e) => setSecurityAnswer(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>
      <Button type="submit" className="w-full gradient-primary text-white">
        Verify Answer
      </Button>
    </form>
  );

  const renderPasswordStep = () => (
    <form onSubmit={handlePasswordSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="newPassword">New Password</Label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id="newPassword"
            type="password"
            placeholder="••••••••"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirmPassword">Confirm New Password</Label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            id="confirmPassword"
            type="password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>
      <Button type="submit" className="w-full gradient-primary text-white">
        Reset Password
      </Button>
    </form>
  );

  const getStepTitle = () => {
    switch (step) {
      case 'email': return 'Reset Password';
      case 'security': return 'Security Verification';
      case 'password': return 'Set New Password';
      default: return 'Reset Password';
    }
  };

  const getStepDescription = () => {
    switch (step) {
      case 'email': return 'Enter your email to get your security question';
      case 'security': return 'Answer your security question to verify your identity';
      case 'password': return 'Create a new password for your account';
      default: return 'Enter your email to get your security question';
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-background to-accent/10 p-4">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-primary mb-4 shadow-custom-lg">
            <Building2 className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold mb-2">Forgot Password</h1>
          <p className="text-muted-foreground">Reset your SMB account password</p>
        </div>

        <Card className="shadow-custom-xl">
          <CardHeader>
            <CardTitle>{getStepTitle()}</CardTitle>
            <CardDescription>{getStepDescription()}</CardDescription>
          </CardHeader>
          <CardContent>
            {step === 'email' && renderEmailStep()}
            {step === 'security' && renderSecurityStep()}
            {step === 'password' && renderPasswordStep()}

            <div className="mt-6 text-center text-sm">
              Remember your password?{' '}
              <Link to="/login" className="text-primary font-medium hover:underline">
                Sign in
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ForgotPassword;